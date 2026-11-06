"""Compile a hardware-free reference encoder using a local ESPHome checkout."""

import re
import subprocess
import sys
from pathlib import Path

# This temporary executable runs upstream code; none of it ships in the MIT package.
src = Path(sys.argv[1]) / "esphome/components"
out = Path(sys.argv[2])
common = '#pragma once\n#include "remote_base.h"\n'
common += """
#include <cmath>
#include <set>
#define ESP_LOGW(...)
#define GETBIT8(v,p) (((v)>>(p))&1)
#define GETBITS8(v,p,n) (((v)>>(p))&((1<<(n))-1))
#define HITACHI_AC424_GETBIT8 GETBIT8
#define HITACHI_AC424_GETBITS8 GETBITS8
#define LOG_STR(x) x
#define USE_WHIRLPOOL_HISENSE_ARG
using LogString=char;
inline uint32_t millis(){return 0;}
inline void assign_bits(uint8_t& v,int mask,bool set){v=set?v|mask:v&~mask;}
inline uint8_t xor_bytes(const uint8_t* p,size_t n,uint8_t init=0){for(size_t i=0;i<n;i++)init^=p[i];return init;}
#define ESP_LOGVV(...)
#define ESP_LOGV_HEX(...)
namespace esphome {
using ::reverse_bits;
template<typename T> T clamp(T v,T lo,T hi){return std::clamp(v,lo,hi);}
constexpr float fahrenheit_to_celsius(float v){return (v-32)*5/9;}
inline float celsius_to_fahrenheit(float v){return v*9/5+32;}
namespace climate {
enum ClimateMode {CLIMATE_MODE_OFF,CLIMATE_MODE_AUTO,CLIMATE_MODE_COOL,CLIMATE_MODE_HEAT,CLIMATE_MODE_FAN_ONLY,CLIMATE_MODE_DRY,CLIMATE_MODE_HEAT_COOL};
enum ClimateFanMode {CLIMATE_FAN_ON,CLIMATE_FAN_OFF,CLIMATE_FAN_AUTO,CLIMATE_FAN_LOW,CLIMATE_FAN_MEDIUM,CLIMATE_FAN_HIGH,CLIMATE_FAN_QUIET,CLIMATE_FAN_MIDDLE};
using ClimateFanModeMask = std::array<ClimateFanMode,4>;
enum ClimateSwingMode {CLIMATE_SWING_OFF,CLIMATE_SWING_VERTICAL,CLIMATE_SWING_HORIZONTAL,CLIMATE_SWING_BOTH};
enum ClimatePreset {CLIMATE_PRESET_NONE,CLIMATE_PRESET_BOOST,CLIMATE_PRESET_SLEEP,CLIMATE_PRESET_ECO,CLIMATE_PRESET_COMFORT,CLIMATE_PRESET_ACTIVITY,CLIMATE_PRESET_HOME,CLIMATE_PRESET_AWAY};
}
inline remote_base::RemoteTransmitData captured;
struct Transmit {remote_base::RemoteTransmitData* get_data(){return &captured;} void perform(){};};
struct Transmitter {Transmit transmit(){captured={};return {};}};
inline Transmitter transmitter;
struct State {
 void publish_state(){}
 climate::ClimateMode mode_before_=climate::CLIMATE_MODE_OFF;
 climate::ClimateMode mode=climate::CLIMATE_MODE_COOL;
 float target_temperature=24;
 std::optional<climate::ClimateFanMode> fan_mode=climate::CLIMATE_FAN_AUTO;
 climate::ClimateSwingMode swing_mode=climate::CLIMATE_SWING_OFF;
 std::optional<climate::ClimatePreset> preset=climate::CLIMATE_PRESET_NONE;
 Transmitter* transmitter_=&transmitter;
 bool fahrenheit_=false; float target_humidity=0; uint8_t last_humidity_=0x66, sub_unit_=0,mode_button_=0;
 uint32_t header_high_=8000,header_low_=4000,bit_high_=600,bit_one_low_=1600,bit_zero_low_=550;
};
}
"""
(out / "climate_stub.h").write_text(common)
# Original constants and encoder functions are compiled against a hardware-free state shim.
specs = [
    ("friedrich", "FriedrichClimate"),
    ("mitsubishi", "MitsubishiClimate"),
    ("noblex", "NoblexClimate"),
    ("hitachi_ac344", "HitachiClimate"),
    ("hitachi_ac424", "HitachiClimate"),
    ("whirlpool", "WhirlpoolClimate"),
]
main = '#include "climate_stub.h"\n#include "aeha_protocol.h"\n#include "haier_protocol.h"\n'
for component, cls in specs:
    h = (src / component / f"{component}.h").read_text()
    prefix = h[
        h.index(f"namespace esphome::{component} {{")
        + len(f"namespace esphome::{component} {{") :
    ]
    prefix = prefix[: prefix.index("class " + cls)]
    cpp = (src / component / f"{component}.cpp").read_text()
    cpp = re.sub(r"^#include[^\n]*\n", "", cpp, flags=re.M)
    body = cpp[
        cpp.index(f"namespace esphome::{component} {{")
        + len(f"namespace esphome::{component} {{") :
    ]
    body = body[: body.rfind("}  // namespace")]
    body = re.sub(
        r"WhirlpoolClimate::WhirlpoolClimate\(\).*?\{\}", "", body, flags=re.S
    )
    # Remove only state-entity and receiver methods; leave original encoding algorithms intact.
    declarations = re.findall(
        r"  static constexpr [^;]+;", h[h.index("class " + cls) :]
    )
    pattern = re.compile(
        r"^[\w:<>, *&]+\b" + cls + r"::(\w+)\([^\n]*(?:\n[^\n]*)?\)\s*\{", re.M
    )
    # Simpler signature match, bounded by parentheses rather than lines.
    pattern = re.compile(
        r"^[\w:<>, *&]+\b" + cls + r"::(\w+)\([^{};]*\)\s*(?:const\s*)?\{", re.M
    )
    matches = list(pattern.finditer(body))
    for match in reversed(matches):
        depth = 1
        end = match.end()
        while depth:
            depth += (body[end] == "{") - (body[end] == "}")
            end += 1
        name = match.group(1)
        keep = name in (
            "transmit_state",
            "operation_mode_",
            "fan_speed_",
            "temperature_",
            "transmit_",
            "set_presets_",
            "alt_mode_",
            "fan_speed_swing_",
            "humidity_",
            "vertical_swing_",
            "horizontal_swing_",
            "health_",
            "power_",
            "quiet_",
            "turbo_",
            "sleep_mode_allowed_",
            "operation_settings_",
            "transmit_off_",
            "transmit_state_",
            "get_power_",
            "set_power_",
            "get_mode_",
            "set_mode_",
            "set_temp_",
            "get_fan_",
            "set_fan_",
            "set_swing_v_",
            "get_swing_v_",
            "set_swing_h_",
            "get_swing_h_",
            "set_button_",
            "get_button_",
            "get_mildew_proof",
            "set_swing_v_toggle_",
            "get_swing_v_toggle_",
            "fixed_temp_mode_",
            "encode_hisense_arg_",
        )
        if keep:
            declaration = match.group(0)[:-1].replace(cls + "::", "") + ";"
            if name == "set_temp_":
                declaration = declaration.replace(
                    "bool set_previous", "bool set_previous = true"
                )
            declarations.append(declaration)
        else:
            body = body[: match.start()] + body[end:]
    extra = {
        "mitsubishi": "std::set<climate::ClimateMode> modes_{climate::CLIMATE_MODE_HEAT}; SetFanMode fan_mode_=MITSUBISHI_FAN_3L; bool fahrenheit_compatibility_=false; HorizontalDirection default_horizontal_direction_=HORIZONTAL_DIRECTION_MIDDLE; VerticalDirection default_vertical_direction_=VERTICAL_DIRECTION_AUTO; uint8_t vertical_vanes_=1;",
        "noblex": "bool powered_on_assumed=false;",
        "whirlpool": "bool powered_on_assumed=false,send_swing_cmd_=false; Model model_=MODEL_DG11J1_3A; uint32_t last_transmit_time_=0; bool is_hisense_arg_() const{return model_==MODEL_HISENSE_ARG;} float temperature_min_(){return model_==MODEL_DG11J1_3A?18:16;} float temperature_max_(){return temperature_min_()+14;}",
    }.get(component, "")
    if component.startswith("hitachi"):
        extra += (
            re.search(r"uint8_t remote_state_\[.*?\};", h, re.S).group(0)
            + "uint8_t previous_temp_=27; void dump_state_(const char*,uint8_t*){}"
        )

    main += (
        f"namespace esphome::{component} {{\n"
        + prefix
        + f"\nclass {cls}: public State {{public:\n"
        + extra
        + "\n".join(declarations)
        + "\n};\n"
        + body
        + "\n}\n"
    )
main += """
void emit(const char* name,int mode,int fan,int temp,int swing) {
 printf("%s:%d:%d:%d:%d %u",name,mode,fan,temp,swing,esphome::captured.carrier);
 for(auto t:esphome::captured.data)if(t)printf(" %d",t);
 printf("\\n");
}
int main(){
"""
for component, cls in specs:
    main += "{using namespace esphome; using namespace esphome::climate;"
    main += ""
    main += """for(int mode:{0,2,3,4,5,6}) for(int fan:{2,3,4,5}) for(int swing:{0,1,2,3}) {
 PLACEHOLDER obj.mode=static_cast<ClimateMode>(mode);obj.fan_mode=static_cast<ClimateFanMode>(fan);obj.swing_mode=static_cast<ClimateSwingMode>(swing);
"""
    main = main.replace("PLACEHOLDER", f"{component}::{cls} obj;")
    main += (
        f'obj.target_temperature={72 if component == "friedrich" else 24};obj.transmit_state();emit("{component}",mode,fan,int(obj.target_temperature),swing);'
        + "}}\n"
    )
main += "}\n"
(out / "climate_main2.cpp").write_text(main)
# Add the original AEHA transport for Mistral.
(out / "aeha_protocol.h").write_text((src / "remote_base/aeha_protocol.h").read_text())
aeha = (src / "remote_base/aeha_protocol.cpp").read_text().split("optional<")[0] + "}\n"
(out / "aeha.cpp").write_text(aeha)
subprocess.run(
    [
        "c++",
        "-std=c++20",
        "-I" + str(out),
        str(out / "climate_main2.cpp"),
        str(out / "aeha.cpp"),
        str(out / "haier.cpp"),
        "-o",
        str(out / "climate_reference2"),
    ],
    check=True,
)
print(subprocess.check_output([str(out / "climate_reference2")], text=True), end="")

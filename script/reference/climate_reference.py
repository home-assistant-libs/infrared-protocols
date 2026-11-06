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
#define ESP_LOGVV(...)
#define ESP_LOGV_HEX(...)
namespace esphome {
using ::reverse_bits;
template<typename T> T clamp(T v,T lo,T hi){return std::clamp(v,lo,hi);}
inline float fahrenheit_to_celsius(float v){return (v-32)*5/9;}
inline float celsius_to_fahrenheit(float v){return v*9/5+32;}
namespace climate {
enum ClimateMode {CLIMATE_MODE_OFF,CLIMATE_MODE_AUTO,CLIMATE_MODE_COOL,CLIMATE_MODE_HEAT,CLIMATE_MODE_FAN_ONLY,CLIMATE_MODE_DRY,CLIMATE_MODE_HEAT_COOL};
enum ClimateFanMode {CLIMATE_FAN_ON,CLIMATE_FAN_OFF,CLIMATE_FAN_AUTO,CLIMATE_FAN_LOW,CLIMATE_FAN_MEDIUM,CLIMATE_FAN_HIGH,CLIMATE_FAN_QUIET};
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
    ("ballu", "BalluClimate"),
    ("delonghi", "DelonghiClimate"),
    ("tcl112", "Tcl112Climate"),
    ("zhlt01", "ZHLT01Climate"),
    ("whynter", "Whynter"),
    ("remko_ar715", "RemkoAr715Climate"),
    ("islandaire", "IslandaireClimate"),
    ("mistral_ir", "MistralIR"),
    ("daikin", "DaikinClimate"),
    ("daikin_arc", "DaikinArcClimate"),
    ("daikin_brc", "DaikinBrcClimate"),
    ("haier_tundra", "HaierTundra"),
    ("airton", "AirtonClimate"),
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
        )
        if keep:
            declarations.append(match.group(0)[:-1].replace(cls + "::", "") + ";")
        else:
            body = body[: match.start()] + body[end:]
    extra = {
        "haier_tundra": "uint8_t unit_=0xA6; bool health_mode_=false,quiet_mode_=false,turbo_mode_=false;",
        "airton": "AirtonSettings settings_{false,true,VerticalDirection::VERTICAL_DIRECTION_OFF}; uint8_t previous_mode_=0; bool set_sleep_mode_state(bool v){settings_.sleep_state=v;return true;}",
    }.get(component, "")
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
    main += f"{component}::{cls} obj;"
    main += """for(int mode:{0,2,3,4,5,6}) for(int fan:{2,3,4,5}) for(int swing:{0,1,2,3}) {
 obj.mode=static_cast<ClimateMode>(mode);obj.fan_mode=static_cast<ClimateFanMode>(fan);obj.swing_mode=static_cast<ClimateSwingMode>(swing);
"""
    main += (
        f'obj.target_temperature={72 if component == "islandaire" else 24};obj.transmit_state();emit("{component}",mode,fan,int(obj.target_temperature),swing);'
        + "}}\n"
    )
main += "}\n"
(out / "climate_main.cpp").write_text(main)
# Add the original AEHA transport for Mistral.
(out / "aeha_protocol.h").write_text((src / "remote_base/aeha_protocol.h").read_text())
aeha = (src / "remote_base/aeha_protocol.cpp").read_text().split("optional<")[0] + "}\n"
(out / "aeha.cpp").write_text(aeha)
subprocess.run(
    [
        "c++",
        "-std=c++20",
        "-I" + str(out),
        str(out / "climate_main.cpp"),
        str(out / "aeha.cpp"),
        str(out / "haier.cpp"),
        "-o",
        str(out / "climate_reference"),
    ],
    check=True,
)
print(subprocess.check_output([str(out / "climate_reference")], text=True), end="")

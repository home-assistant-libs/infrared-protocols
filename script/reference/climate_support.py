"""Shared hardware shim and source extraction for the local C++ reference runner."""

import re
from pathlib import Path

common = '#pragma once\n#include "remote_base.h"\n'
common += """
#include <cmath>
#include <set>
#define ESP_LOGW(...)
#define GETBIT8(v,p) (((v)>>(p))&1)
#define GETBITS8(v,p,n) (((v)>>(p))&((1<<(n))-1))
#define LOG_STR(x) x
#define USE_WHIRLPOOL_HISENSE_ARG
#define USE_GREE_FAHRENHEIT
#define USE_GREE_YAW1F
using LogString=char;
inline uint32_t millis(){return 0;}
inline void assign_bits(uint8_t& v,int mask,bool set){v=set?v|mask:v&~mask;}
#define ESP_LOGVV(...)
#define ESP_LOGV_HEX(...)
#define ESP_LOGD_HEX(...)
namespace esphome {
using ::reverse_bits;
template<typename T> T clamp(T v,T lo,T hi){return std::clamp(v,lo,hi);}
constexpr float fahrenheit_to_celsius(float v){return (v-32)*5/9;}
constexpr float celsius_to_fahrenheit(float v){return v*9/5+32;}
namespace climate {
// SOURCE_ENUMS
}
inline remote_base::RemoteTransmitData captured;
inline std::vector<remote_base::RemoteTransmitData> transmissions;
struct Transmit {remote_base::RemoteTransmitData* get_data(){return &captured;} void perform(){transmissions.push_back(captured);};};
struct Transmitter {Transmit transmit(){captured={};return {};}};
inline Transmitter transmitter;
namespace remote_base { struct RemoteTransmitterBase { using TransmitCall=Transmit; }; }
struct State {
 template<typename Protocol,typename Data> void transmit_(const Data& data){auto call=transmitter_->transmit();Protocol().encode(call.get_data(),data);call.perform();}
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

KEEP = (
    "add_",
    "alt_mode_",
    "encode_",
    "encode_fan_",
    "encode_hisense_arg_",
    "encode_mode_",
    "fan_speed_",
    "fan_speed_swing_",
    "finalize_frame",
    "fixed_temp_mode_",
    "gen_checksum_",
    "get_button_",
    "get_fan_",
    "get_mildew_proof",
    "get_mode_",
    "get_power_",
    "get_swing_h_",
    "get_swing_v_",
    "get_swing_v_toggle_",
    "health_",
    "horizontal_swing_",
    "humidity_",
    "operation_mode_",
    "operation_settings_",
    "power_",
    "quiet_",
    "reverse_",
    "reverse_add_",
    "seiya_swing_code_",
    "set_blades_",
    "set_button_",
    "set_fan_",
    "set_fan_speed_",
    "set_mode_",
    "set_power_",
    "set_presets_",
    "set_swing_h_",
    "set_swing_v_",
    "set_swing_v_toggle_",
    "set_temp_",
    "sleep_mode_allowed_",
    "temperature_",
    "transmit_",
    "transmit_generic_",
    "transmit_off_",
    "transmit_rac_pt1411hwru_",
    "transmit_rac_pt1411hwru_temp_",
    "transmit_ras_2819t_",
    "transmit_state",
    "transmit_state_",
    "turbo_",
    "vertical_swing_",
)
EXTRAS = {
    "gree": "Model model_=GREE_GENERIC; uint8_t feature_bits_=0; bool use_fahrenheit_=false;",
    "haier_tundra": "uint8_t unit_=0xA6; bool health_mode_=false,quiet_mode_=false,turbo_mode_=false;",
    "airton": "AirtonSettings settings_{false,true,VerticalDirection::VERTICAL_DIRECTION_OFF}; uint8_t previous_mode_=0; bool set_sleep_mode_state(bool v){settings_.sleep_state=v;return true;}",
    "mitsubishi": "std::set<climate::ClimateMode> modes_{climate::CLIMATE_MODE_HEAT}; SetFanMode fan_mode_=MITSUBISHI_FAN_3L; bool fahrenheit_compatibility_=false; HorizontalDirection default_horizontal_direction_=HORIZONTAL_DIRECTION_MIDDLE; VerticalDirection default_vertical_direction_=VERTICAL_DIRECTION_AUTO; uint8_t vertical_vanes_=1;",
    "noblex": "bool powered_on_assumed=false;",
    "whirlpool": "bool powered_on_assumed=false,send_swing_cmd_=false; Model model_=MODEL_DG11J1_3A; uint32_t last_transmit_time_=0; bool is_hisense_arg_() const{return model_==MODEL_HISENSE_ARG;} float temperature_min_(){return model_==MODEL_DG11J1_3A?18:16;} float temperature_max_(){return temperature_min_()+14;}",
    "emmeti": "uint8_t blades_=EMMETI_BLADES_STOP;",
    "toshiba": "Model model_=MODEL_GENERIC; climate::ClimateSwingMode last_swing_mode_=climate::CLIMATE_SWING_OFF; climate::ClimateMode last_mode_=climate::CLIMATE_MODE_OFF; std::optional<climate::ClimateFanMode> last_fan_mode_; float last_target_temperature_=0,current_temperature=24; void* sensor_=nullptr; uint8_t encode_mode_fan_(){return encode_mode_()|encode_fan_();}",
}
SPECS = [
    ("ballu", "BalluClimate"),
    ("delonghi", "DelonghiClimate"),
    ("tcl112", "Tcl112Climate"),
    ("zhlt01", "ZHLT01Climate"),
    ("whynter", "Whynter"),
    ("remko_ar715", "RemkoAr715Climate"),
    ("islandaire", "IslandaireClimate"),
    ("mistral_ir", "MistralIR"),
    ("daikin_arc", "DaikinArcClimate"),
    ("daikin_brc", "DaikinBrcClimate"),
    ("haier_tundra", "HaierTundra"),
    ("airton", "AirtonClimate"),
    ("friedrich", "FriedrichClimate"),
    ("mitsubishi", "MitsubishiClimate"),
    ("noblex", "NoblexClimate"),
    ("hitachi_ac344", "HitachiClimate"),
    ("hitachi_ac424", "HitachiClimate"),
    ("whirlpool", "WhirlpoolClimate"),
    ("toshiba", "ToshibaClimate"),
    ("emmeti", "EmmetiClimate"),
    ("gree", "GreeClimate"),
    ("pd_pioneer_ir", "PDPioneerIR"),
]


def extract_climate(
    src: Path,
    component: str,
    cls: str,
    *,
    filename=None,
    base="State",
    keep=KEEP,
    extra=None,
    nested=False,
) -> str:
    filename = filename or component
    h = (src / component / f"{filename}.h").read_text()
    prefix = h[
        h.index(f"namespace esphome::{component} {{")
        + len(f"namespace esphome::{component} {{") :
    ]
    class_start = re.search(r"class\s+" + cls + r"(?:\s+final)?\s*:", prefix).start()
    prefix = prefix[:class_start]
    cpp = (src / component / f"{filename}.cpp").read_text()
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
        if name in keep:
            declaration = match.group(0)[:-1].replace(cls + "::", "") + ";"
            if name == "reverse_add_":
                declaration = "template<typename T> " + declaration
            if name == "transmit_rac_pt1411hwru_temp_":
                declaration = declaration.replace(
                    "const bool cs_state", "const bool cs_state = true"
                ).replace(
                    "const bool cs_send_update", "const bool cs_send_update = true"
                )
            if name == "set_temp_" and component.startswith("hitachi"):
                declaration = declaration.replace(
                    "bool set_previous", "bool set_previous = true"
                )
            declarations.append(declaration)
        else:
            body = body[: match.start()] + body[end:]
    extra = EXTRAS.get(component, "") if extra is None else extra
    if component.startswith("hitachi"):
        extra += (
            re.search(r"uint8_t remote_state_\[.*?\};", h, re.S).group(0)
            + "uint8_t previous_temp_=27; void dump_state_(const char*,uint8_t*){}"
        )
    return (
        f"namespace esphome::{component}{'::reference' if nested else ''} {{\n"
        + prefix
        + f"\nclass {cls}: public {base} {{public:\n"
        + extra
        + "\n".join(declarations)
        + "\n};\n"
        + body
        + "\n}\n"
    )


def prepare_stub(src: Path, out: Path) -> None:
    """Use the checkout's actual enums instead of maintaining numbered copies."""
    header = (src / "climate/climate_mode.h").read_text()
    enums = "\n".join(
        re.findall(
            r"enum (?:ClimateMode|ClimateFanMode|ClimateSwingMode|ClimatePreset)\s*:[^{]+\{.*?\};",
            header,
            re.S,
        )
    )
    stub = common.replace(
        "// SOURCE_ENUMS",
        enums + "\nusing ClimateFanModeMask = std::array<ClimateFanMode,4>;",
    )
    (out / "climate_stub.h").write_text(stub)

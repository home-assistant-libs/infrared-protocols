"""Build every climate reference with one shared shim and fresh state per case."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

from cases import cases
from climate_support import SPECS, extract_climate, prepare_stub


def generate(source: Path, out: Path) -> str:
    """Compile the supplied checkout and record every emitted transmission."""
    src = source / "esphome/components"
    prepare_stub(src, out)
    for directory in ("remote_base", "climate"):
        (out / "esphome/components" / directory).mkdir(parents=True, exist_ok=True)
    (out / "esphome/components/climate/climate_mode.h").write_text(
        '#include "climate_stub.h"\n'
    )
    for name in ("aeha", "haier", "toshiba_ac", "pd_pioneer"):
        shutil.copy(src / f"remote_base/{name}_protocol.h", out / f"{name}_protocol.h")
    shutil.copy(
        out / "pd_pioneer_protocol.h",
        out / "esphome/components/remote_base/pd_pioneer_protocol.h",
    )
    for suffix in ("h", "cpp"):
        shutil.copy(
            src / f"pd_pioneer_ir/pd_pioneer_data.{suffix}",
            out / f"pd_pioneer_data.{suffix}",
        )
    aeha = (src / "remote_base/aeha_protocol.cpp").read_text().split("optional<")[
        0
    ] + "}\n"
    (out / "aeha.cpp").write_text(aeha)
    main = '#include "climate_stub.h"\n#include "aeha_protocol.h"\n#include "haier_protocol.h"\n#include "toshiba_ac_protocol.h"\n#include "pd_pioneer_data.h"\n#define USE_GREE_YAW1F\n'
    specs = SPECS
    for component, cls in specs:
        main += extract_climate(src, component, cls)
    ras_header = (src / "toshiba/ras_25j2kvsg_nd.h").read_text()
    extra = ras_header[
        ras_header.index("  enum class ToshibaPreset") : ras_header.index(
            "  static ToshibaPreset custom_preset_at"
        )
    ]
    extra += "ToshibaPowerSelection power_selection_=ToshibaPowerSelection::TOSHIBA_POWER_SELECTION_100;uint32_t swing_ignore_until_=0;uint8_t fan_code_()const{return encode_fan_();}"
    main += extract_climate(
        src,
        "toshiba",
        "ToshibaRas25j2kvsgNdClimate",
        filename="ras_25j2kvsg_nd",
        base="ToshibaClimate",
        extra=extra,
        keep=("transmit_frame_", "encode_motion_", "transmit_motion_", "perform_"),
        nested=True,
    )
    main += """
struct Input { const char* key; int mode,fan; float temperature; int swing; };
void emit(const char* key) {
 if(esphome::transmissions.empty())esphome::transmissions.push_back(esphome::captured);
 size_t index=0;
 for(const auto& tx:esphome::transmissions){
  printf("%s@%zu %u",key,index++,tx.carrier);
  for(auto t:tx.data)if(t)printf(" %d",t);
  printf("\\n");
 }
}
int main(){using namespace esphome;using namespace esphome::climate;
"""
    inputs = cases()
    groups = dict.fromkeys(
        (
            case["component"],
            case.get("setup", ""),
            case.get("invoke", "obj.transmit_state();"),
        )
        for case in inputs
    )
    for component, setup, invoke in groups:
        group = [
            case
            for case in inputs
            if (
                case["component"],
                case.get("setup", ""),
                case.get("invoke", "obj.transmit_state();"),
            )
            == (component, setup, invoke)
        ]
        main += (
            "{Input inputs[]={\n"
            + ",\n".join(
                '{"%s",%d,%d,%sf,%d}'
                % (c["key"], c["mode"], c["fan"], float(c["temperature"]), c["swing"])
                for c in group
            )
            + "};for(auto input:inputs){transmissions.clear();captured={};\n"
        )
        family = (
            component.split("_")[0]
            if component.startswith(("toshiba_", "gree_"))
            else component
        )
        cls = (
            "reference::ToshibaRas25j2kvsgNdClimate"
            if component == "toshiba_6"
            else dict(specs)[family]
        )
        main += f"{family}::{cls} obj;\n"
        if family in ("toshiba", "gree"):
            main += f"obj.model_=static_cast<{family}::Model>({component[-1]});\n"
        if family == "gree":
            main += "obj.feature_bits_=gree::default_feature_bits(obj.model_);\n"
        main += """obj.mode=static_cast<ClimateMode>(input.mode);
obj.fan_mode=static_cast<ClimateFanMode>(input.fan);
obj.swing_mode=static_cast<ClimateSwingMode>(input.swing);
obj.target_temperature=input.temperature;
"""
        main += setup + invoke
        main += "emit(input.key);}}\n"
    main += "}\n"
    (out / "climate_main.cpp").write_text(main)
    (out / "climate_inputs.json").write_text(json.dumps(inputs))
    subprocess.run(
        [
            "c++",
            "-std=c++20",
            "-I" + str(out),
            str(out / "climate_main.cpp"),
            *[
                str(out / name)
                for name in (
                    "aeha.cpp",
                    "haier.cpp",
                    "pd_pioneer.cpp",
                    "pd_pioneer_data.cpp",
                )
            ],
            "-o",
            str(out / "climate_reference"),
        ],
        check=True,
    )
    return subprocess.check_output([str(out / "climate_reference")], text=True)


if __name__ == "__main__":
    print(generate(Path(sys.argv[1]), Path(sys.argv[2])), end="")

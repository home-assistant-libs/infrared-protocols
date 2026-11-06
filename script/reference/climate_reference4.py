"""Compile a hardware-free reference encoder using a local ESPHome checkout."""

import shutil
import subprocess
import sys
from pathlib import Path

src = Path(sys.argv[1]) / "esphome/components"
out = Path(sys.argv[2])
(out / "esphome/components/remote_base").mkdir(parents=True, exist_ok=True)
(out / "esphome/components/climate").mkdir(parents=True, exist_ok=True)
(out / "esphome/components/climate/climate_mode.h").write_text(
    '#include "climate_stub.h"\n'
)
shutil.copy(
    src / "remote_base/pd_pioneer_protocol.h",
    out / "esphome/components/remote_base/pd_pioneer_protocol.h",
)
shutil.copy(src / "pd_pioneer_ir/pd_pioneer_data.h", out / "pd_pioneer_data.h")
shutil.copy(src / "pd_pioneer_ir/pd_pioneer_data.cpp", out / "pd_pioneer_data.cpp")
h = (src / "gree/gree.h").read_text()
h = h[h.index("namespace esphome::gree {") : h.index("class GreeClimate final")]
cpp = (src / "gree/gree.cpp").read_text()
cpp = cpp[
    cpp.index("namespace esphome::gree {") : cpp.index("void GreeClimate::set_model")
]
main = (
    '#include "climate_stub.h"\n#include "pd_pioneer_data.h"\n#define USE_GREE_YAW1F\n'
    + h
    + "}\n"
    + cpp
    + "}\n"
)
main += """
void emit(const char* name,int mode,int fan,int temp,int swing) {
 printf("%s:%d:%d:%d:%d %u",name,mode,fan,temp,swing,esphome::captured.carrier);
 for(auto t:esphome::captured.data)if(t)printf(" %d",t);
 printf("\\n");
}
int main(){using namespace esphome;using namespace esphome::climate;
for(int mode:{0,2,3,4,5,6})for(int fan:{2,3,4,5})for(int swing:{0,1,2,3}){
 pd_pioneer_ir::ControlData data;
 data.set_mode(static_cast<ClimateMode>(mode));
 if(mode!=0&&mode!=4)data.set_temp(24);
 data.set_fan_mode(static_cast<ClimateFanMode>(fan));
 data.set_swing_mode(static_cast<ClimateSwingMode>(swing));data.finalize();captured={};
 remote_base::PDPioneerProtocol().encode(&captured,data.odd());remote_base::PDPioneerProtocol().encode(&captured,data.even());
 emit("pd_pioneer_ir",mode,fan,24,swing);
 for(int model=0;model<9;model++){
  auto m=static_cast<gree::Model>(model);
  gree::GreeClimateData state{.mode=static_cast<ClimateMode>(mode),.target_temperature=24,.fan_mode=static_cast<ClimateFanMode>(fan),.swing_mode=static_cast<ClimateSwingMode>(swing),.preset=CLIMATE_PRESET_NONE,.feature_bits=gree::default_feature_bits(m)};
  captured={};gree::GreeProtocol(m).encode(&captured,gree::GreeClimateCodec::encode(m,state));
  char name[16];sprintf(name,"gree_%d",model);emit(name,mode,fan,24,swing);
 }
}
}
"""
(out / "climate_main4.cpp").write_text(main)
subprocess.run(
    [
        "c++",
        "-std=c++20",
        "-I" + str(out),
        str(out / "climate_main4.cpp"),
        str(out / "pd_pioneer_data.cpp"),
        str(out / "pd_pioneer.cpp"),
        "-o",
        str(out / "climate_reference4"),
    ],
    check=True,
)
print(subprocess.check_output([str(out / "climate_reference4")], text=True), end="")

"""Compile a hardware-free reference encoder using a local ESPHome checkout."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

src = Path(sys.argv[1]) / "esphome/components/remote_base"
out = Path(sys.argv[2]) / "extra"
shutil.copytree(
    Path(sys.argv[2]), out, dirs_exist_ok=True, ignore=shutil.ignore_patterns("extra")
)
p = out / "remote_base.h"
p.write_text(p.read_text() + "\nusing std::clamp;\n")
names = ["ira211", "dyson", "lg"]
for n in names:
    shutil.copy(src / f"{n}_protocol.h", out / f"{n}_protocol.h")
    s = (src / f"{n}_protocol.cpp").read_text()
    i = s.index("optional<")
    if n == "ira211":
        i = s.index("optional<IRA211Data> IRA211Protocol::decode")
    (out / f"{n}.cpp").write_text(s[:i] + "\n}\n")
main = (
    "\n".join(f'#include "{n}_protocol.h"' for n in names)
    + """
using namespace esphome::remote_base;
void emit(const char* name, const RemoteTransmitData& d){printf("%s %u",name,d.carrier);for(auto t:d.data)printf(" %d",t);printf("\\n");}
int main(){
"""
)
for a in (1, 2, 4, 5, 6, 7):
    main += (
        "{RemoteTransmitData d; IRA211Protocol().encode(&d, IRA211Data{.command=static_cast<IRA211Command>("
        + str(a)
        + '),.half_degrees=43,.mode=IRA211Mode::IRA211_MODE_TIMER,.fan=IRA211Fan::IRA211_FAN_HIGH});emit("ira211_'
        + str(a)
        + '",d);}\n'
    )
main += """{RemoteTransmitData d; DysonProtocol().encode(&d,DysonData{.code=0x1234,.index=2});emit("dyson",d);}
{RemoteTransmitData d; LGProtocol().encode(&d,LGData{.data=0xABCDEFA,.nbits=28});emit("lg28",d);}
{RemoteTransmitData d; LGProtocol().encode(&d,LGData{.data=0xABCDEFAB,.nbits=32});emit("lg32",d);}
}
"""
(out / "extra.cpp").write_text(main)
subprocess.run(
    [
        "c++",
        "-std=c++20",
        "-I" + str(out),
        str(out / "extra.cpp"),
        *[str(out / f"{n}.cpp") for n in names],
        "-o",
        str(out / "extra"),
    ],
    check=True,
)
raw = subprocess.check_output([str(out / "extra")], text=True)
print(raw, end="")

inputs = {
    f"ira211_{action}": {
        "command": action,
        "half_degrees": 43,
        "mode": "TIMER",
        "fan": "HIGH",
    }
    for action in (1, 2, 4, 5, 6, 7)
}
inputs.update(
    {
        "dyson": {"code": 0x1234, "index": 2},
        "lg28": {"data": 0xABCDEFA, "nbits": 28},
        "lg32": {"data": 0xABCDEFAB, "nbits": 32},
    }
)
(out / "inputs.json").write_text(json.dumps(inputs))

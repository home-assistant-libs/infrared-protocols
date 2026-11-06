"""Compile a hardware-free reference encoder using a local ESPHome checkout."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

src = Path(sys.argv[1]) / "esphome/components/remote_base"
out = Path(sys.argv[2])
out.mkdir(exist_ok=True)
(out / "esphome/core").mkdir(parents=True, exist_ok=True)
common = """#pragma once
#include <algorithm>
#include <array>
#include <cstdint>
#include <cstddef>
#include <cstring>
#include <cstdio>
#include <cstdlib>
#include <cinttypes>
#include <optional>
#include <vector>
#include <string>
using std::clamp;
#define PROGMEM
#define ESPHOME_LOG_TAG(name, value) static const char* name=value;
#define ESP_LOGI(...)
#define ESP_LOGV(...)
#define ESP_LOGD(...)
#define ESP_LOGE(...)
#define PROGMEM_STRING_TABLE(...)
#define DECLARE_REMOTE_PROTOCOL(...)
inline void progmem_memcpy(void* a, const void* b, size_t n) { memcpy(a,b,n); }
inline uint8_t progmem_read_byte(const uint8_t* p) { return *p; }
template<size_t N> constexpr size_t format_hex_pretty_size() {return N*3+1;}
constexpr size_t format_hex_pretty_size(size_t n) {return n*3+1;}
template<typename... T> const char* format_hex_pretty_to(T...) {return "";}
inline uint8_t reverse_bits(uint8_t b) { uint8_t r=0; for(int i=0;i<8;i++) {r=(r<<1)|(b&1);b>>=1;}return r; }
inline void put_be16(uint8_t* p,uint16_t v){p[0]=v>>8;p[1]=v;}
inline void put_be32(uint8_t* p,uint32_t v){for(int i=0;i<4;i++)p[i]=v>>(24-i*8);}
inline uint8_t xor_bytes(const uint8_t* p,size_t n,uint8_t init=0){for(size_t i=0;i<n;i++)init^=p[i];return init;}
inline uint8_t sum_bytes(const uint8_t* p,size_t n,uint8_t init=0) {for(size_t i=0;i<n;i++)init+=p[i];return init;}
namespace esphome {
using std::optional;
namespace remote_base {
using RawTimings=std::vector<int32_t>;
using RawTimingsView=const RawTimings&;
enum class BitOrder { BIT_ORDER_LSB_FIRST, BIT_ORDER_MSB_FIRST };
struct BitTimings { uint32_t bit_mark=0, one_space=0, zero_space=0; BitOrder bit_order=BitOrder::BIT_ORDER_LSB_FIRST; uint32_t one_mark=0,zero_mark=0; };
class RemoteTransmitData {
 public:
 RawTimings data; uint32_t carrier=0;
 void set_carrier_frequency(uint32_t v){carrier=v;}
 void reserve(size_t){}
 void reset(){data.clear();}
 void mark(uint32_t t){data.push_back(t);}
 void space(uint32_t t){data.push_back(-int32_t(t));}
 void item(uint32_t m,uint32_t s){mark(m);space(s);}
 const RawTimings& get_data() const {return data;}
 template<BitTimings T> void item_bytes(const uint8_t* p,size_t n){
  for(size_t i=0;i<n;i++)for(int j=0;j<8;j++){
   int bit=(p[i]>>(T.bit_order==BitOrder::BIT_ORDER_MSB_FIRST?7-j:j))&1;
   item(T.bit_mark?T.bit_mark:(bit?T.one_mark:T.zero_mark),bit?T.one_space:T.zero_space);
  }
 }
};
class RemoteReceiveData { public: bool expect_item(int,int){return false;} bool expect_mark(int){return false;} bool expect_space(int){return false;} template<BitTimings T> bool expect_bytes(uint8_t*,size_t){return false;} };
template<typename T> class RemoteProtocol {};
}
}
"""
(out / "remote_base.h").write_text(common)
for name in ["log", "helpers", "hal", "component", "progmem"]:
    (out / f"esphome/core/{name}.h").write_text(
        '#pragma once\n#include "remote_base.h"\n'
    )
names = "jvc dish samsung36 toto roomba hob2hood magiquest gobox beo4 canalsat haier mirage midea coolix pd_pioneer pioneer_wyt toshiba_ac ira211 dyson lg".split()
for name in names:
    shutil.copy(src / f"{name}_protocol.h", out / f"{name}_protocol.h")
    cpp = (src / f"{name}_protocol.cpp").read_text()
    # Preserve upstream encoder code solely in this temporary reference executable.
    marker = (
        "optional<IRA211Data> IRA211Protocol::decode"
        if name == "ira211"
        else "optional<"
    )
    pos = cpp.find(marker)
    if pos >= 0:
        cpp = cpp[:pos] + "\n} // namespace\n"
    (out / f"{name}.cpp").write_text(cpp)
main = (
    """#include "remote_base.h"
"""
    + "".join(f'#include "{name}_protocol.h"\n' for name in names)
    + """
using namespace esphome::remote_base;
void emit(const char* name, const RemoteTransmitData& d) {
 printf("%s %u",name,d.carrier);
 for(auto t:d.data)printf(" %d",t);
 printf("\\n");
}
int main() {
"""
)
cases = [
    ("jvc", "JVCProtocol().encode(&d,JVCData{0xA55A});"),
    ("dish", "DishProtocol().encode(&d,DishData{.address=4,.command=37});"),
    (
        "samsung36",
        "Samsung36Protocol().encode(&d,Samsung36Data{.address=0x1234,.command=0xABCDE});",
    ),
    (
        "toto",
        "TotoProtocol().encode(&d,TotoData{.code=0xB79C});",
    ),
    ("roomba", "RoombaProtocol().encode(&d,RoombaData{0xA5});"),
    (
        "hob2hood",
        "Hob2HoodProtocol().encode(&d,Hob2HoodData{HOB2HOOD_COMMAND_FAN_MEDIUM});",
    ),
    (
        "magiquest_legacy",
        "MagiQuestProtocol().encode(&d,MagiQuestData{.magnitude=0xABCD,.wand_id=0x12345678});",
    ),
    ("gobox", "GoboxProtocol().encode(&d,GoboxData{GOBOX_MENU});"),
    (
        "beo4",
        "Beo4Protocol().encode(&d,Beo4Data{.source=0x12,.command=0xA5,.repeats=0});",
    ),
    (
        "canalsat",
        "CanalSatProtocol().encode(&d,CanalSatData{.device=0x12,.address=0x23,.repeat=0,.command=0x56});",
    ),
    (
        "canalsatld",
        "CanalSatLDProtocol().encode(&d,CanalSatData{.device=0x12,.address=0x23,.repeat=0,.command=0x56});",
    ),
    (
        "haier",
        "const uint8_t data[]={0xA5,1,2,3,4,5,6,7}; HaierProtocol().encode(&d,data,8);",
    ),
    (
        "mirage",
        "const uint8_t data[]={0xA5,1,2,3,4,5,6,7,8,9,10,11,12,13}; MirageProtocol().encode(&d,data,14);",
    ),
    (
        "midea",
        "MideaData data{0xA1,0x81,0x48,0xFF,0xFF,0}; data.finalize(); MideaProtocol().encode(&d,data);",
    ),
    ("coolix", "CoolixProtocol().encode(&d,CoolixData(0xB21FC8,0xB2BFE4));"),
    (
        "pd_pioneer",
        "PDPioneerData data{0x23,0xCB,0x26,1,0,0x24,3,7,5,0x80,0,0,0,0}; data.finalize(); PDPioneerProtocol().encode(&d,data);",
    ),
    (
        "pioneer_wyt",
        "PioneerWytData data{0x23,0xCB,0x26,2,0,0x24,3,7,5,0x80,0,0,0,0}; data.finalize(); PioneerWytProtocol().encode(&d,data);",
    ),
    (
        "toshiba_ac",
        "ToshibaAcProtocol().encode(&d,ToshibaAcData{0x123456789ABC,0xABCDEF012345});",
    ),
]
cases.extend(
    (
        f"ira211_{action}",
        f"IRA211Protocol().encode(&d, IRA211Data{{.command=static_cast<IRA211Command>({action}),.half_degrees=43,.mode=IRA211Mode::IRA211_MODE_TIMER,.fan=IRA211Fan::IRA211_FAN_HIGH}});",
    )
    for action in (1, 2, 4, 5, 6, 7)
)
cases.extend(
    [
        ("dyson", "DysonProtocol().encode(&d,DysonData{.code=0x1234,.index=2});"),
        ("lg28", "LGProtocol().encode(&d,LGData{.data=0xABCDEFA,.nbits=28});"),
        ("lg32", "LGProtocol().encode(&d,LGData{.data=0xABCDEFAB,.nbits=32});"),
    ]
)
inputs = {name: {"encoder": expression} for name, expression in cases}
inputs["toto"]["repeat"] = {
    "times": 3,
    "wait_time": 36000,
    "source": "esphome/components/remote_base/__init__.py::_toto_default_repeat",
}
(out / "inputs.json").write_text(json.dumps(inputs))
for name, expr in cases:
    main += "{RemoteTransmitData d; " + expr + f' emit("{name}",d);' + "}\n"
main += "}\n"
(out / "main.cpp").write_text(main)
subprocess.run(
    [
        "c++",
        "-std=c++20",
        "-I" + str(out),
        str(out / "main.cpp"),
        *[str(out / f"{name}.cpp") for name in names],
        "-o",
        str(out / "reference"),
    ],
    check=True,
)
print(subprocess.check_output([str(out / "reference")], text=True), end="")

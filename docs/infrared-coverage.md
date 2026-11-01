# Infrared protocol coverage

This expansion implements the native infrared families present in ESPHome at
`27aa91bb9d4fc270d535e0e9ace4ff4582a13cef` (November 1, 2026).
The Python implementations remain MIT licensed. Wire layouts, timings and
checksums were implemented independently; ESPHome was used as a behavioral
reference. No ESPHome C++ runtime code is included or required at runtime.
This is not a claim of clean-room development: the reference sources were read.

## New transports

Each entry supports encoding and decoding unless explicitly marked otherwise.
A transport carries numeric fields or bytes; it does not imply a complete named
button catalog for every appliance using it.

| Device category | New transport classes | Higher-level command families |
| --- | --- | --- |
| TV, audio and set-top boxes | `JvcCommand`, `Samsung36Command`, `Lg28Command`, `Lg32Command`, `DishCommand`, `Beo4Command`, `CanalSatCommand`, `CanalSatLDCommand`, `GoboxCommand` | Gobox's 13 named remote buttons |
| Fans | `DysonCommand` (13-bit code and rolling index) | Existing Dyson Cool and AM09 button families gain decoders |
| Kitchen extractors | `Hob2HoodCommand` | Fan off/four speeds; light on/off |
| Robot vacuums | `RoombaCommand` | Raw command byte |
| Toilets and bidets | `TotoCommand` | Remote ID nibbles and command byte |
| Interactive toys | `MagiQuestCommand` | Physical wand ID, magnitude and checksum; separate transmit-only `MagiQuestLegacyCommand` matches ESPHome's legacy transmitter layout |
| HVAC and thermostats | `HaierCommand`, `MirageCommand`, `CoolixCommand`, `MideaCommand`, `PdPioneerCommand`, `PioneerWytCommand`, `ToshibaAcPacketCommand`, `Ira211Command` | Climate state and actions listed below; Haier/Mirage/Pioneer WYT also expose raw packets |

`Ira211Command` models the Siemens IRA211 thermostat's temperature up/down,
mode, fan, power-button and full-state synchronization actions. Its mode is
protection/timer/comfort, rather than the common air-conditioner mode vocabulary.

## New climate command families

All families below have encoders and decoders. The classes live under
`infrared_protocols.commands`; module names are shown for direct imports.

| Family | Module and public classes | Model-specific commands and settings |
| --- | --- | --- |
| Airton | `airton.AirtonCommand` | Power, mode, fan, temperature, vertical direction, display, sleep |
| Ballu | `ballu.BalluCommand` | Complete state and both swing axes |
| Coolix | `coolix.CoolixCommand.climate()` | State; named off, swing, light, silence/frost-protection buttons in `codes.coolix.climate` |
| Daikin | `daikin.DaikinCommand` | State, both swing axes, quiet fan and presets |
| Daikin ARC | `daikin_arc.DaikinArcCommand`, `DaikinArcQueryCommand` | State, humidity selection, sensor query |
| Daikin BRC | `daikin_brc.DaikinBrcCommand`, `DaikinBrcFahrenheitCommand` | Celsius/Fahrenheit variants, subunit selection, mode-button indicator |
| DeLonghi | `delonghi.DelonghiCommand` | State with mode-dependent temperature ranges |
| Emmeti | `emmeti.EmmetiCommand` | State, dedicated off, fixed positions and swing ranges |
| Friedrich | `friedrich.FriedrichCommand`, `FriedrichUtilityCommand` | Native Fahrenheit state, economy, separate power-off and louver actions |
| Haier Tundra | `haier_tundra.HaierTundraCommand` | Unit A/B, both swing axes, health, quiet/turbo, light/self-clean button identifiers |
| Hitachi | `hitachi.HitachiAc344Command`, `HitachiAc424Command` | 344/424-bit variants, native button identifiers, vane positions, mildew protection |
| Islandaire | `islandaire.IslandaireCommand` | Native Fahrenheit heat/cool/fan state |
| Midea | `midea.MideaCommand.climate()`, `.follow_me()` | State, sleep, Celsius/Fahrenheit, remote sensor reports; named swing-step, swing-toggle and turbo-toggle actions in `codes.midea.climate` |
| Mistral | `mistral.MistralCommand` | State and swing |
| Mitsubishi Electric | `mitsubishi.MitsubishiCommand` | Native fan levels, Celsius/Fahrenheit remote table, both vane axes, dual vanes, economy/night/powerful presets |
| Noblex | `noblex.NoblexCommand` | State and vertical swing; mode correction described below |
| Pioneer PD | `pd_pioneer_climate.PdPioneerClimateCommand` | Paired state packets, half-degree set points, both swing axes, economy |
| Remko AR715 | `remko_ar715.RemkoAr715Command` | Cool/dry/fan, temperature and vertical swing |
| TCL112 | `tcl112.Tcl112Command` | State, half-degree set points, vertical swing |
| Toshiba | `toshiba.ToshibaCommand`, `ToshibaRasB10n3kv2Command`, `ToshibaSeiyaCommand`, `ToshibaRas25j2kvsgNdCommand`; `toshiba_48.ToshibaRacCommand`, `ToshibaRas2819Command` | Generic, RAC Celsius/Fahrenheit, RAS-2819, RAS-B10N3KV2, Seiya and RAS-25J2KVSG-ND; model-dependent off/swing, Comfort Sense, power selection, boost/eco/fireplace/frost/Hada Care/sleep presets, separate vane-step and swing-toggle actions |
| Whirlpool / Hisense | `whirlpool.WhirlpoolCommand`, `WhirlpoolDg11j191Command`, `HisenseArgCommand` | DG11J1-3A, DG11J1-91, Hisense/BGH Argentina; explicit power/swing toggles, Hisense absolute swing |
| Whynter | `whynter.WhynterCommand` | Celsius/Fahrenheit state |
| ZHLT01 | `zhlt01.Zhlt01Command` | State, both swing axes, boost and sleep fan |

These cover 25 newly added ESPHome climate components, counting Hitachi's two
components and Siemens IRA211 separately. A family can expose several models.

### Expanded existing families

- **Panasonic heat pumps:** DKE, JKE, LKE, NKE, CKP, RKR and PKE from the earlier
  Panasonic branch are included. Full state and regional Quiet/Powerful packets
  now decode, including checksum validation and explicit CKP toggle semantics.
- **Gree:** `gree_models.GreeModelCommand` supports Generic, YAN, YAA, YAC,
  YAC1FB9, YB1FA, YX1FF, YAG and YAW1F. It adds model-specific swing axes,
  supported turbo/light/health/XFan features, sleep, Fahrenheit display encoding
  and YAW1F's required follow-up packet. Decoding requires the model argument.
  The original `GreeAcCommand` API remains available.
- **Existing transport decoders:** AEHA, Kaseikyo, RC5, RC6, Marantz Extended
  (RC5X), Pioneer, Samsung32, Sony 12/15/20 and Dyson Cool/AM09.
  RC6 additionally accepts a three-bit mode selector for its existing 8+8-bit
  payload layout; this does not add longer RC6A/MCE payloads.

Existing NEC, Symphony, Pronto, Fujitsu, General Electric, Samsung AC and LG AC
implementations are retained. This inventory describes additions, not a claim
that every model sold under each brand uses the same protocol.

## Integration API

```python
from infrared_protocols.commands.climate import ClimateFan, ClimateMode
from infrared_protocols.commands.daikin import DaikinCommand

command = DaikinCommand(
    mode=ClimateMode.HEAT,
    temperature=21,
    fan=ClimateFan.AUTO,
    swing_v=True,
)
raw = command.get_raw_timings()  # signed microseconds: mark positive, space negative
carrier = command.modulation  # Hz
received = DaikinCommand.from_raw_timings(raw)
if received is not None:
    state = received.state
```

The new climate families use `ClimateMode`, `ClimateFan` and `ClimateState` where
applicable. Decoded common temperatures are Celsius, including families whose
constructors accept native Fahrenheit. A `None` state field means the message
does not establish that value. Raw received payloads retain auxiliary fields
outside the common state. Existing protocol APIs retain their own field types.

Integrations must choose the protocol/model, send the timings through their IR
hardware, and retain assumed state for toggle-only controls. This library does
not create Home Assistant entities or infer appliance state from transmission.

## Scope and validation limits

- HeatpumpIR is an external GPLv2 library, not native ESPHome protocol code. Its
  wrapper and external encoder catalog are excluded from this MIT expansion.
  RF and wired protocols (including Onkyo RI) are outside infrared scope.
- New multi-section climate decoders expect a complete logical packet. They do
  not implement ESPHome's streaming receive/state machine, assemble sections
  across callbacks, or accept all truncated section-only captures. Supply the
  full capture; protocol-specific decoders that accept one complete repeat
  document that behavior.
- Full state cannot always be recovered. Whirlpool/CKP carry power toggles;
  Hisense auto-temperature ranges and Toshiba RAS-2819 dry temperatures can be
  ambiguous. Candidate values are available rather than invented exact values.
- Noblex assigns the declared mode field explicitly. ESPHome currently ORs the
  field into a cool template, changing auto/dry/heat codes. Those corrected
  modes require hardware confirmation and are excluded from exact-reference
  comparisons. Hitachi AUTO is rejected because the reference encodes cooling
  for it. Emmeti's upstream high-swing value aliases full swing on the wire.
- Synthetic reference checks compare exact carrier/timings for 27 transport
  examples and 2,419 climate combinations (1,846 distinct family/waveform cases
  retained as SHA-256 fixtures). Additional tests cover semantic actions,
  decoder boundaries, checksum rejection and timing jitter. These are software
  comparisons, not new physical-device captures. Advanced model features have
  semantic/round-trip coverage rather than exhaustive reference combinations.
- Panasonic PKE additionally has the physical remote recordings documented in
  the main README. Hardware confirmation is still needed for other target
  devices before relying on an HA integration.

The factual reference is the cloned
[ESPHome source revision](https://github.com/esphome/esphome/tree/27aa91bb9d4fc270d535e0e9ace4ff4582a13cef/esphome/components).
Reference fixture metadata records that revision. GPL source was compiled only
in a temporary comparison harness and is not distributed in this package.

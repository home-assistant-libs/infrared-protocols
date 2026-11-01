# Python Infrared Protocols for Home Assistant

Python package to decode and encode infrared signals for use in Home Assistant.

This library exists to support [Home Assistant](https://www.home-assistant.io/)
integrations. It is not intended as a general-purpose, standalone infrared
library, and its API is driven by the needs of Home Assistant Core. Changes
should be motivated by a concrete use case in
[home-assistant/core](https://github.com/home-assistant/core); see the pull
request template for details.

There is no requirement to implement a given protocol or its codes in this
library. An integration may use a separate, dedicated library instead, as long
as that library depends on this one for the underlying types. This library's
primary role is to provide the shared, foundational types that the Home
Assistant ecosystem can build on.

## Panasonic heat pumps

`PanasonicAcCommand` supports the DKE, JKE, LKE, NKE, CKP, RKR, and PKE
216-bit protocol variants. An HA climate integration can build a complete
state command and send it through an infrared entity:

```python
from infrared_protocols.commands.panasonic_ac import (
    PanasonicAcCommand,
    PanasonicAcMode,
    PanasonicAcModel,
)

command = PanasonicAcCommand(
    model=PanasonicAcModel.PKE,
    mode=PanasonicAcMode.HEAT,
    temperature=21,
    power=True,
)
timings = command.get_raw_timings()
carrier_frequency = command.modulation
```

Named models support whole-degree set points from 16 to 30 °C, fan-only mode,
five fan speeds plus auto, and five fixed vertical vane positions plus auto.
The auto vane setting lets the unit choose its position; it does not guarantee
continuous swinging. `frost_protection=True` with heat mode sends 10 °C,
maximum fan, and automatic vane positioning while the integration retains the
ordinary set point.

CKP uses a power toggle. Pass `power_toggle=True` to change power or `False`
to leave it unchanged, instead of `power`. The integration must track the
current power state. DKE and RKR accept `swing_axis2`; the other named models
use a fixed value for that field.

Omitting `model` preserves the original regional encoding, including half-degree
set points and nanoeX. The named models do not support nanoeX or the existing
regional Quiet/Powerful toggle commands. `from_raw_timings()` decodes complete
state packets; pass the same `model` to interpret a named remote variant.
`PanasonicAcToggleCommand.from_raw_timings()` handles regional toggle packets.

The model layouts and PKE recording fixtures come from
[ESPHome's Panasonic IR component](https://github.com/esphome/esphome/pull/21631).
PKE frames are checked against recordings from a CS-NE9PKE remote. The other
variants are checked against the ESPHome encoding; hardware validation is still
needed for an integration using this library.

## Additional infrared protocols

The ESPHome coverage expansion adds native IR transports and climate command
families while retaining this package's MIT license. See the
[coverage and API guide](docs/infrared-coverage.md) for the device-category tables,
model variants, new decoders, named button families and validation limits.

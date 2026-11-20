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

The generic Gree profile keeps its original framing and timings. YAP1F/YAP1FB
uses captured pulse means (8796/4365 µs leader, 673 µs marks, 516/1580 µs
zero/one spaces) and three inter-burst spaces of 19500, 39000, and 19500 µs.
Its four bursts are block A, block B, the fixed continuation's block A and block
B; each gap follows a burst, and the final timing is the last mark.
Pass `model=GreeAcModel.YAP1F` when constructing and decoding.
The fixed continuation is `000000a0` / `000000a0`. Countdown-timer captures
also include a companion pair between the state and fixed pairs; decoding
validates its state tag and checksum without interpreting its LCD payload.
Both profiles use `display`, `anion`, and `blow`; for a YAP1F remote
these correspond to light, health, and X-FAN respectively. YAP1F carries the
full generic state (power, mode, temperature, fan, swing, turbo, sleep, timer,
and fresh air). Clock, wall-clock timers, and weekly schedule have no known
wire mapping and are not encoded. YAP1F vertical vane positions are supported;
self-clean has no verified wire location.

The Gree command also encodes Fahrenheit setpoints, energy-saving mode, horizontal
vane positions, and display-temperature source using the field layout documented by
[IRremoteESP8266 `ir_Gree.h`/`ir_Gree.cpp`](https://github.com/crankyoldgit/IRremoteESP8266).
The 2026-10-02 YAP1F captures confirm Fahrenheit setpoints, energy saving,
display-temperature source, and both swing axes. `swing_h_position` retains
the wire nibble: 0 off, 1 sweep, 2–6 fixed positions, and YAP1F-only 12 and 13.
Session three confirms selection 12 with swing stopped; its physical position
is not established. Selection 13 is sweep.
On YAP1F, `swing_h` can explicitly preserve whether the latched horizontal
selection is moving; omitted values infer movement for positions 1 and 13.
Session two captures positions 0, 1, 2, 5, 6, and 13; positions 3 and 4 still
lack captures. Session three captures vertical 5 in two intact, checksummed
state pairs with damaged fixed tails; vertical 2 still lacks a verified capture.
YAP1F encoding preserves the explicit `swing_v` movement flag independently
of the latched vertical-position nibble, including stopped position 9.
`display_temp` selects 0 off, 1 setpoint, 2 indoor, or 3 outdoor; set
`fahrenheit=True` for a 61–86 °F setpoint. `econo` represents the energy-saving bit;
the Gree manual describes this function for cool mode. The YAP1F CLOCK+TEMP
combination also drives this bit: in heat it is the absence (8 °C frost
protection) function, captured 2026-10-02, and encoded as `absence=True`. The
wire bit is shared, so either flag sets it and decoding a YAP1F frame with the
bit set reports both. The reference does not define a child-lock bit, so it is
not encoded.

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
Pass `model=GreeAcModel.YAP1F` when constructing and decoding. The continuation
repeats bytes 0-2, echoes the fan in byte 6, and carries its own checksum.
Both profiles use `display`, `anion`, and `blow`; for a YAP1F remote
these correspond to light, health, and X-FAN respectively. YAP1F carries the
full generic state (power, mode, temperature, fan, swing, turbo, sleep, timer,
and fresh air). Clock, wall-clock timers, and weekly schedule have no known
wire mapping and are not encoded. Vane positions and self-clean
are not supported without verified wire locations.

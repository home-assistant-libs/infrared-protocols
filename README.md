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

The Gree AC command supports the existing generic framing (the default) and a
three-block YAP1F profile. Pass `model=GreeAcModel.YAP1F` when constructing and
decoding. Both profiles use `display`, `anion`, and `blow`; for a YAP1F remote
these correspond to light, health, and X-FAN respectively. YAP1F also supports
power, mode, temperature, fan, and turbo. Its decoder checks both checksums and
overlapping bytes, tolerates quantized pulse timings, and emits valid nonzero raw
encoder output ending in the final mark. Its decoder accepts the final mark with
either no trailing space or a long trailing space. Vane controls and self-clean
are not supported without verified wire locations.

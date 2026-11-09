# Climate command guidance

Read this when adding or changing climate/AC commands. General contributor rules are in [AGENTS.md](../AGENTS.md).

## Native models and state

- Model the device's native values. No shared climate enums or universal state templates; Home Assistant integrations normalize.
- If two models interpret the same bytes differently, require the caller to select the model. For example, one model may use a bit for swing while another uses it for a fixed vane position. Document these differences; do not guess the model from the signal.
- Name fan enums `<Family>FanSpeed` and the wire unit flag `is_fahrenheit`. For input conversion without a wire unit flag, use a distinct name such as Mitsubishi's `fahrenheit_compatibility`.
- Include only fields the family can carry. Decode absent or ambiguous fields (e.g. temperature in fan-only) as `None`; constructors accept `None` there. Keep retained wire values separate when needed to rebuild a packet.
- Distinguish absolute state, toggles, relative actions, auxiliary frames and sensor reports. An action or follow-up packet must not manufacture a complete climate state.
- Constructor and decoded types match: `int` for whole-degree, `float` for fractional setpoints; native units and enums survive readback.
- Validate explicitly supplied values even when the mode sends a fixed wire value.
- Use wire-valued enums for direct mappings, without lookup tables. Use plain `Enum` when different model enums share a union: equal-valued `IntEnum` members compare equal.
- Avoid duplicate readback paths for fields already in `state`.

## Reconstruction and testing

- Decode → public constructor → encode must reproduce the frame, including variant, features, positions, units and actions, using only received values. Document exceptions for captured variants the encoder cannot reproduce.
- When accepting a standalone state section, reconstruct any required constant sections for transmission.
- Cover off frames, fixed-temperature modes, native units and ambiguous candidates.
- Pass decoded fields directly into constructors in tests so the type checker checks the caller's rebuild path.
- Cover every distinct packet shape and each family's models, modes, temperature limits/steps, fans, units and features. Don't repeat timing-only checks per equivalent setting.

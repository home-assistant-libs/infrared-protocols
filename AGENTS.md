# Agent Instructions

`infrared-protocols` is a pure-Python library (Python ≥ 3.14) that encodes infrared remote-control protocols (e.g. NEC) to and from raw pulse/space timing sequences. The public API surface is small and intentionally minimal.

## Environment Setup

```bash
./script/setup.sh
```

## Git Commit Guidelines

- **Do NOT amend, squash, or rebase commits that have already been pushed to the PR branch after the PR is opened** - Reviewers need to follow the commit history, as well as see what changed since their last review

## Lint / Format / Type-check

- After finishing a code session, run `prek --all-files` to run all lint, format, and type-check hooks.

## Code Style

- Write code that reads like the surrounding code. `infrared_protocols/commands/nec.py` and `infrared_protocols/codes/lg/tv.py` are good references.
- No `Any`; avoid `cast`; prefer real type narrowing.
- Constructor arguments are keyword-only (use the `*` separator).
- Use `# fmt: skip` on long arrays of numbers to avoid having one number per line. Break them at around 100 column length.
- Keep comments concise. Prefer one short line stating the non-obvious constraint, or no comment at all.
- Do not add comments that just restate the code on the following line(s) (e.g. `# Check if initialized` above `if self.initialized:`). Comments should only explain why (non-obvious constraints, surprising behavior, or workarounds), never what. Comments in tests that explain why a function call or assertion is made are ok.


## Python 3.14 Notes

- Do not flag Python 3.14 syntax as an issue or suggest workarounds for older versions.
- `except TypeA, TypeB:` without parentheses is valid in Python 3.14, and annotations are evaluated lazily (PEP 649), so forward references in annotations never need quoting.

## Protocol Semantics

- Only expose repeat handling when the protocol itself defines how a held key is transmitted: either a distinct repeat-code frame (NEC, Kaseikyo) or retransmission of the full frame on a fixed frame period (RC-5, RC-6, Samsung32).
- Do not add a generic "send it N times" knob to an encoder whose protocol says nothing about repetition, and do not invent a frame period the protocol does not specify.

### Before implementing a protocol

- Read the existing implementations and tests before designing a new class. Identify overlapping transports, models, enums and timing helpers; reuse them where their semantics match.
- Decide the model boundaries and public API before expanding to more families. Identical framing does not establish identical model semantics: require an explicit model when the signal cannot identify it, and document overlapping decoders and intentional differences.
- Preserve this library's MIT license. Implement from protocol facts and captured signals; do not copy incompatible licensed implementation code into the library. Keep external reference implementations confined to the comparison harness.

### Native APIs and state

- Represent the device's native models, values and capabilities. Home Assistant integrations own normalization; do not introduce shared climate enums or a universal state template that loses native fan levels, units, vane positions or alternate codes.
- Follow existing naming and constructor conventions, including `<Family>FanSpeed` and `is_fahrenheit` where the protocol carries a unit choice. An input-only display conversion must have a distinct name and documented readback semantics.
- Include only fields the family can carry. Within that family, use `None` for fields absent, inactive or ambiguous in a particular command. Fixed off/auto/dry/fan-only/frost bytes are not automatically an active mode or setpoint. Keep retained wire values separate when needed to rebuild a packet.
- Distinguish absolute state, toggles, relative actions, auxiliary frames and sensor reports. Do not manufacture a complete state from an action or treat a follow-up packet as a new climate setting.
- Keep constructor and decoded-state types compatible: whole-degree temperatures use `int`, fractional setpoints use `float`, and native units and enum types survive readback. Accept `None` where a decoded command legitimately lacks mode or temperature; require values where the frame needs them. Validate explicitly supplied invalid values even when a mode uses a fixed wire value.
- Expose meaningful received fields through the public API and provide corresponding encoder inputs where supported. Rebuilding a command must not silently lose features, positions, units or action details. Avoid duplicate readback paths for fields already in `state`.
- Reuse enums for identical fields. Use wire-valued enums where there is a direct mapping, without identity lookup tables. When different model enums share a public union, check equality and dictionary-key behavior: unrelated `IntEnum` members with the same integer collide; use plain `Enum` where identity must remain distinct.
- Keep one authoritative payload. Encoding, state and native properties must describe the same validated bytes after any supported mutation; avoid independently writable copies or stale caches.
- Use inheritance only where the public contract holds. Keep internal helpers private and share framing/checksum code instead of duplicating it or exposing options that a subclass can only reject.

### Receiver and transmission behavior

- Check the complete transmission: carrier, bit order, header variant, checksums/parity, required copies, follow-up frames, gaps and held-key cadence. Do not equate mandatory copies with optional held-key repeats, or identical application sections with repeats.
- Preserve the detected variant and meaningful framing when re-encoding. When accepting a standalone state section, reconstruct required constant sections for a valid transmission where the protocol defines them.
- Design for actual receiver boundaries. ESPHome defaults to a 10 ms idle timeout; headers, section gaps and inter-copy gaps can split a press. Test single and joined captures, all public capture entry points, custom idle values and jitter near a split threshold. Document caller grouping requirements and ambiguities.
- Handle clock scaling in both directions, fixed mark/space bias, trailing idle and a final space merged into idle. Choose tolerances from protocol evidence and captures. Manchester/NRZ run quantization must not silently change decoded bits.
- Validate all complete frames and repeated payloads. Tolerate a clipped final repeat only when the available prefix matches the expected next frame and a complete command is already known. Reject damaged intermediate frames, conflicting trailers and incomplete preamble/button pairs.
- Validate model-specific field combinations, not just individual ranges. A decoder may accept documented captured variants that the encoder does not generate; make that distinction explicit and test it.

## Error Handling

- No custom exception classes: incorrect inputs surface as built-in exceptions (`TypeError`, `ValueError`) with descriptive messages.
- Correctness is enforced primarily through the type checker and immutable value objects rather than defensive runtime checks.

## Testing

- Prefer `@pytest.mark.usefixtures` over arguments when the argument is not used.
- Avoid conditions/branching in tests: split tests or adjust the parametrization to cover all cases without branching.
- If multiple tests share most of their code, merge them with `pytest.mark.parametrize`, naming cases via `pytest.param` with an `id`.
- Keep protocol tests in `tests/commands/test_<protocol>.py` and code-table tests in `tests/codes/test_<brand>_<module>.py`. Reserve cross-family tests for shared helpers or fixture contracts; do not create files named after review rounds. Test code-table uniqueness and follow the existing `to_command() -> Command` convention.
- Establish independent expected bytes/timings and decoded native values. Encoder-to-decoder round trips alone cannot catch a shared wrong lookup table or checksum. Assert all relevant public fields and their types; numeric equality alone misses `24.0` versus `24` and collisions between enums.
- Test decode → rebuild through the public constructor → encode using only received values, including auxiliary properties, without borrowing original constructor inputs. Cover off frames with `mode=None`, fixed-temperature modes with `temperature=None`, native units, retained fields and ambiguous candidates. Include typed calls so static incompatibilities are caught. Explicitly identify action factories or captured variants outside this rebuild contract.
- Build a coverage matrix for each family: models, modes (including off/auto/dry/fan-only), temperature limits and increments, fans, units, features, positions and actions. Cover meaningful interactions and every distinct packet shape; avoid repeating timing-only checks for every equivalent setting.
- Add recorded captures where available and realistic scaling/bias/split/truncation cases. Assert exact decoded fields under distortion, not merely a non-`None` result. Synthetic signals are not evidence of hardware validation.
- Exercise rejection rules with bad checksums/parity, headers, polarity, lengths, model identifiers, conflicting repeats and invalid field combinations. Ask whether deleting a validation or changing a wire constant would leave the tests green.
- Keep fixture expectations native, without converting through a generic climate vocabulary. Use explicit per-factory build/decode/rebuild callbacks instead of family type switches or string-based exclusions. Remove redundant assertions and generic scaffolding when moving tests into protocol files.

## Reference Fixtures

- Fixture metadata must retain source repositories, full revisions, inputs and whether signals are recorded captures or synthetic encoder outputs. A link in the PR body alone is insufficient. Record each capture's source and distinguish encoder output from harness-added repeats or framing.
- Regenerate ESPHome fixtures from a clean checkout at the recorded revision with a C++20 compiler:

  ```bash
  uv run python script/reference/generate.py /path/to/ESPHome --output /tmp/infrared-reference
  ```

- Compare every generated fixture with the committed version before replacing it. Pin source revisions for reproducibility and explicitly review changes when updating them.
- Use the source encoder in the comparison harness rather than retyping its logic. Keep cases independent; model stateful transitions with explicit setup. Capture every transmission, and fail on omitted cases or extraction drift instead of silently dropping unmatched rows.
- Keep inputs, native expectations and case generation together. Cover boundaries and non-default features, not thousands of combinations at one temperature. Store inspectable outputs so failures show what differs, rather than hashes alone. Document evidence-backed deviations from reference behavior instead of reproducing reference bugs.

## Before Requesting Review

- Audit the whole affected family set when fixing a shared invariant. A finding about absent temperatures, native types, stale state or capture boundaries is a prompt to check sibling implementations, not just the cited line.
- Review the full diff for consistency with existing APIs, tests and docstrings. After an API refactor, remove obsolete adapters, unused tables, duplicate properties and stale documentation. Run relevant tests and all required hooks on the final changes; verify CI belongs to the current head.

## AI policy

This project follows the [Open Home Foundation AI Policy](AI_POLICY.md).
Autonomous contributions are not accepted: a human must review, understand, and be able to explain every change before it is submitted. Do not open issues or pull requests autonomously, and do not post comments on behalf of a user without their review.

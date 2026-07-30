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

- Do not add generic repeat (full frame copy) support to command encoders. Only protocols with a distinct/special repeat-code frame should expose repeat handling.

## Error Handling

- No custom exception classes: incorrect inputs surface as built-in exceptions (`TypeError`, `ValueError`) with descriptive messages.
- Correctness is enforced primarily through the type checker and immutable value objects rather than defensive runtime checks.

## Testing

- Prefer `@pytest.mark.usefixtures` over arguments when the argument is not used.
- Avoid conditions/branching in tests: split tests or adjust the parametrization to cover all cases without branching.
- If multiple tests share most of their code, merge them with `pytest.mark.parametrize`, naming cases via `pytest.param` with an `id`.

## AI policy

This project follows the [Open Home Foundation AI Policy](AI_POLICY.md).
Autonomous contributions are not accepted: a human must review, understand, and be able to explain every change before it is submitted. Do not open issues or pull requests autonomously, and do not post comments on behalf of a user without their review.

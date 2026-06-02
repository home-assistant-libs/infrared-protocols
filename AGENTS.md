# Agent Instructions

`infrared-protocols` is a pure-Python library (Python ≥ 3.14) that encodes infrared
remote-control protocols (e.g. NEC) to and from raw pulse/space timing sequences.
The public API surface is small and intentionally minimal.

## Environment Setup

```bash
./script/setup.sh
```

## Git Commit Guidelines

- **Do NOT amend, squash, or rebase commits that have already been pushed to the PR branch after the PR is opened** - Reviewers need to follow the commit history, as well as see what changed since their last review

## Build / Lint / Test

- `ruff` is used for linting and formatting.
- `basedpyright` is used for type checking.
- `pytest` is used for testing.
- After finishing a code session, run `prek --all-files` to check for linting and formatting issues.

### Run all lint, format, and type-check hooks (changed files only)
```bash
prek
```

### Run all hooks on every file
```bash
prek --all-files
```

## Code Style

### Imports
- **Within the package:** use relative imports to the specific submodule that
  defines the symbol, e.g. `from . import Command` in
  `infrared_protocols/commands/nec.py` (picking up `Command` from the
  `commands` package's `__init__.py`).

### Types
- No `Any`; avoid `cast`; prefer real type narrowing.
- Inline variable annotations where needed: `timings: list[int] = []`.

### Classes
- Abstract base classes use `abc.ABC` and `@abc.abstractmethod`.
- Immutable value objects use `@dataclass(frozen=True, slots=True)`.
- Constructor arguments should be **keyword-only** (use `*` separator) to prevent
  positional-argument confusion.

### Docstrings
- First line: concise one-line summary.
- Multi-line: blank line after the summary, then prose description when the method is
  complex or requires extra detail.

## Python Syntax Notes

- Python 3.14 and above is supported. Do not flag syntax or features that require Python 3.13 as issues, and do not suggest workarounds for older Python versions.
- Python 3.14 explicitly allows `except TypeA, TypeB:` without parentheses. Never flag this as an issue.
- Python 3.14 evaluates annotations lazily (PEP 649). Forward references in annotations do not need to be quoted — annotations can reference names defined later in the module without quoting them or using `from __future__ import annotations`. Do not flag unquoted forward references in annotations as issues.

## Protocol Semantics

- Do not add generic repeat (full frame copy) support to command encoders. Only
  protocols with a distinct/special repeat-code frame should expose repeat handling.

## Error Handling

- The library currently has no custom exceptions. Incorrect inputs surface as natural
  Python runtime errors (`TypeError`, `ValueError`).
- Correctness is enforced primarily through the type checker and immutable value
  objects rather than defensive runtime checks.
- If you add validation, raise standard built-in exceptions with descriptive messages
  rather than introducing custom exception classes unless there is a clear consumer
  need.

## Testing

- Use `pytest` to run tests
- When writing or modifying tests, ensure all test function parameters have type annotations.
- Prefer concrete types over `Any`.
- Prefer `@pytest.mark.usefixtures` over arguments, if the argument is not going to be used.
- Avoid using conditions/branching in tests. Instead, either split tests or adjust the test parametrization to cover all cases without branching.
- If multiple tests share most of their code, use `pytest.mark.parametrize` to merge them into a single parameterized test instead of duplicating the body. Use `pytest.param` with an `id` parameter to name the test cases clearly.

## Good practices

- Do not add comments that just restate the code on the following line(s) (e.g. `# Check if initialized` above `if self.initialized:`). Comments should only explain why — non-obvious constraints, surprising behavior, or workarounds — never what.

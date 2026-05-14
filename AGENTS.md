`infrared-protocols` is a pure-Python library (Python ≥ 3.13) that encodes infrared
remote-control protocols (e.g. NEC) to and from raw pulse/space timing sequences.
The public API surface is small and intentionally minimal.

## Environment Setup

```bash
./script/setup.sh
```

## Build / Lint / Test

- `ruff` is used for linting and formatting.
- `basedpyright` is used for type checking.
- `pytest` is used for testing.

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

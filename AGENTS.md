# AGENTS.md — infrared-protocols

Guidelines for agentic coding agents working in this repository.

---

## Project Overview

`infrared-protocols` is a pure-Python library (Python ≥ 3.13) that encodes infrared
remote-control protocols (e.g. NEC) into raw pulse/space timing sequences. The public
API surface is small and intentionally minimal.

---

## Environment Setup

```bash
# Bootstrap dev environment (uses uv)
./script/setup.sh

# Equivalent manual step
uv pip install -e ".[dev]"
```

Dev extras install: `pytest`, `prek` (lint/format/type-check runner).

---

## Build / Lint / Test Commands

### Run all lint, format, and type-check hooks (changed files only)
```bash
prek
```

### Run all hooks on every file
```bash
prek --all-files
```

### Run linter only (with auto-fix)
```bash
ruff check --fix infrared_protocols/
```

### Run formatter only
```bash
ruff format infrared_protocols/
```

### Run type checker only
```bash
basedpyright infrared_protocols/
```

### Run all tests
```bash
pytest --log-cli-level=debug
```

### Run a single test file
```bash
pytest tests/test_commands.py
```

### Run a single test by name
```bash
pytest tests/test_commands.py::test_nec_command_get_raw_timings_standard
```

> CI tests against Python 3.13 and 3.14 via GitHub Actions.

---

## Repository Structure

```
infrared_protocols/      # Library source (only this directory is linted/type-checked)
    __init__.py          # Public API: defines __all__ and re-exports
    commands.py          # All domain logic: Command ABC, NECCommand
    loader.py            # Flipper `.ir` parser + get_codes / CommandCollection
    codes/               # Bundled Flipper `.ir` code files (packaged as data)
        lg/tv.ir
        nedis/vmat3462at.ir
tests/
    test_commands.py     # Command encoding tests
    test_loader.py       # Loader tests
script/
    setup.sh             # Dev environment bootstrap
.pre-commit-config.yaml  # ruff, ruff-format, basedpyright hooks
pyproject.toml           # Build config, ruff rules, pyright settings
```

### Bundled IR codes

IR code sets live under `infrared_protocols/codes/<vendor>/<device>.ir` as
Flipper Zero `.ir` files. They are loaded at runtime via `get_codes(path)`
(see `loader.py`). `get_codes` returns a `CommandCollection`; the backing
file is parsed lazily on the first `await collection.load_command(...)` and
cached. To add a new device, drop a `.ir` file under `codes/<vendor>/` — no
Python changes required.

---

## Code Style

### Formatting
- Enforced by `ruff-format` (Black-compatible).
- **Indentation:** 4 spaces.
- **Quotes:** Double quotes (`"..."`).
- **Line length:** 88 characters (Black default).
- **Trailing commas:** Required in multi-line collections and argument lists.
- **Semicolons:** Never.
- Two blank lines between top-level definitions; one blank line between methods.

### Imports
- **Within the package:** use relative imports (`from .commands import ...`).
- **In tests:** use absolute imports from the installed package (`from infrared_protocols import ...`).
- Named imports only; no wildcard imports (`from x import *`).
- Import order is enforced by ruff's `I` (isort) rules: stdlib → third-party → local.
- `__all__` must be defined in `__init__.py` to explicitly declare the public API.

### Naming
| Element | Convention | Example |
|---|---|---|
| Files / modules | `snake_case` | `commands.py` |
| Packages | `snake_case` | `infrared_protocols` |
| Classes | `PascalCase` | `NECCommand`, `CommandCollection` |
| Functions / methods | `snake_case` | `get_raw_timings` |
| Variables / attributes | `snake_case` | `high_us`, `repeat_count` |
| Local numeric constants | `snake_case` (not `UPPER_CASE`) | `leader_high = 9000` |
| Test functions | `test_<subject>_<description>` | `test_nec_command_get_raw_timings_standard` |
| Hex literals | Uppercase hex digits | `0xFF`, `0x04FB` |

> Note: Local numeric constants intentionally use `snake_case` rather than
> `SCREAMING_SNAKE_CASE`. Follow this convention throughout.

### Types
- Type checker: `basedpyright` with `typeCheckingMode = "standard"`.
- **All** function parameters and return types must be annotated.
- `-> None` must be explicit on `__init__` and void methods.
- Use PEP 585 lowercase generics: `list[int]`, not `List[int]`.
- Use PEP 604 union syntax: `T | None`, not `Optional[T]`.
- Use `@override` (from `typing`, Python 3.12+) on every overridden method.
- No `Any`; avoid `cast`; prefer real type narrowing.
- Inline variable annotations where needed: `timings: list[int] = []`.

### Classes
- Abstract base classes use `abc.ABC` and `@abc.abstractmethod`.
- Immutable value objects use `@dataclass(frozen=True, slots=True)`.
- Constructor arguments should be **keyword-only** (use `*` separator) to prevent
  positional-argument confusion.

### Docstrings
- All public classes and methods must have a docstring.
- First line: concise one-line summary.
- Multi-line: blank line after the summary, then prose description. No Google/NumPy
  parameter sections unless complexity demands it.

```python
def get_raw_timings(self) -> list[int]:
    """Get raw timings for the NEC command.

    NEC protocol timing (in microseconds):
    - Leader pulse: 9000µs high, 4500µs low
    ...
    """
```

---

## Architecture

### Adding a New Protocol
1. Subclass `Command` (ABC) in `infrared_protocols/commands.py`.
2. Implement `get_raw_timings(self) -> list[int]` (signed: +mark / -space µs).
3. Decorate the override with `@override`.
4. Define timing constants as local `snake_case` variables inside the method.
5. Re-export the new class from `infrared_protocols/__init__.py` and add it to
   `__all__`.

### Key Abstractions
- **Timings** — a flat `list[int]` of signed microseconds. Positive values are
  marks (carrier on), negative values are spaces (carrier off). Lists alternate
  mark/space starting with a mark; an unpaired trailing mark is allowed (and
  conventional for an end pulse).
- **`Command` (ABC)** — base class for all IR protocol encoders. Holds `modulation`
  and `repeat_count`.
- **`NECCommand(Command)`** — encodes the NEC protocol; reference implementation.

### Patterns to Follow
- Build timing lists by appending signed ints (positive mark, then negative space).
- Repeat-code frame gaps are appended as a single negative int that turns the
  previous bare end-pulse mark into a mark+space pair (see `NECCommand`).
- Bit manipulation uses masks like `data & 1`, `data >>= 1`, `(~x) & 0xFF`.

---

## Testing

- No mocking. Tests use pure value comparison against manually constructed
  `list[int]` fixtures.
- One assertion per logical case; reuse expected values with list unpacking
  (`[*expected[:-1], ...]`) rather than duplicating fixtures.
- Tests live in `tests/test_commands.py`; keep them in one file unless the suite
  grows substantially.
- Pre-commit hooks (`prek`) do **not** run on `tests/`; the type checker and linter
  only target `infrared_protocols/`. Tests are still expected to be clean Python.

---

## Error Handling

- The library currently has no custom exceptions. Incorrect inputs surface as natural
  Python runtime errors (`TypeError`, `ValueError`).
- Correctness is enforced primarily through the type checker and immutable value
  objects rather than defensive runtime checks.
- If you add validation, raise standard built-in exceptions with descriptive messages
  rather than introducing custom exception classes unless there is a clear consumer
  need.

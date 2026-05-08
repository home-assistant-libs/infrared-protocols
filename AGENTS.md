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
pytest tests/commands/test_nec.py
```

---

## Code Style

### Imports
- **Within the package:** use relative imports to the specific submodule that
  defines the symbol, e.g. `from . import Command` in
  `infrared_protocols/commands/nec.py` (picking up `Command` from the
  `commands` package's `__init__.py`).
- **In tests:** import directly from the protocol submodule, e.g.
  `from infrared_protocols.commands.nec import NECCommand`. Do not import from
  `infrared_protocols` or `infrared_protocols.commands` — neither re-exports
  protocol classes.
- Named imports only; no wildcard imports (`from x import *`).
- Import order is enforced by ruff's `I` (isort) rules: stdlib → third-party → local.
- No re-exports of protocol classes. The top-level `infrared_protocols/__init__.py`
  is empty so importing a code module only loads the protocol encoder it actually
  needs. The `commands/__init__.py` defines the `Command` ABC directly (there is
  no separate `base.py`); concrete protocol classes live in their own submodules
  and are not re-exported.

### Naming
| Element | Convention | Example |
|---|---|---|
| Files / modules | `snake_case` | `nec.py`, `samsung.py` |
| Packages | `snake_case` | `infrared_protocols` |
| Classes | `PascalCase` | `NECCommand`, `Command` |
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
1. Create `infrared_protocols/commands/<protocol>.py` and subclass `Command` (ABC)
   via `from . import Command` (the ABC lives in `commands/__init__.py`).
2. Implement `get_raw_timings(self) -> list[int]`.
3. Decorate the override with `@override`.
4. Define timing constants as local `snake_case` variables inside the method.
5. Add `tests/commands/test_<protocol>.py` for the new encoder, importing
   directly from `infrared_protocols.commands.<protocol>`.

### Key Abstractions
- **Raw timings** — a flat `list[int]` of microsecond durations. Positive values are
  pulse (high) durations; negative values are space (low) durations. A transmission
  that ends on a pulse is represented by a trailing positive int with no paired
  space.
- **`Command` (ABC)** — base class for all IR protocol encoders. Holds `modulation`
  and `repeat_count`.

### Patterns to Follow
- Build timing lists by starting with a base list, appending pulse/space ints in a
  loop, then using `extend()` for repeat frames.
- Repeat-code frame gaps are appended as a negative int directly after the preceding
  end-pulse (see `NECCommand`).
- Bit manipulation uses masks like `data & 1`, `data >>= 1`, `(~x) & 0xFF`.

---

## Testing

- No mocking. Tests use pure value comparison against manually constructed
  `list[int]` fixtures of signed pulse/space durations.
- One assertion per logical case; reuse expected values with list unpacking
  (`[*expected, ...]`) rather than duplicating fixtures.
- Test layout mirrors the package layout: `tests/commands/test_<protocol>.py`
  (e.g. `tests/commands/test_nec.py`). Each test file imports directly from the
  matching `infrared_protocols.commands.<protocol>` module.
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

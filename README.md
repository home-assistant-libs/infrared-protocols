# Python Infrared Protocols for Home Assistant

Python package to decode and encode infrared signals for use in Home Assistant.

## Loading bundled codes

IR codes are stored as [Flipper Zero `.ir`](https://docs.flipper.net/infrared/file-format)
files under `infrared_protocols/codes/`. `load_codes` returns a
`CommandCollection` without touching the disk; file I/O is deferred to the
first `await collection.load_command(...)` and dispatched to the running
loop's default executor.

```python
from infrared_protocols import load_codes

codes = load_codes("lg/tv")  # no I/O

power = await codes.load_command("POWER")  # parses + caches on first call
await async_send_command(power)
```

`load_command` returns a `Command` (e.g. `NECCommand`). Raises `ValueError`
for unknown command names.

### Custom code directories

Pass `base_dir` to load codes from outside the packaged directory:

```python
from pathlib import Path

codes = load_codes("my_device", base_dir=Path("~/ir-codes").expanduser())
```

Paths are resolved and must stay within `base_dir`; traversal escapes are
rejected. Only the `NEC` and `NECext` Flipper protocols are supported today.

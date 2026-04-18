"""Loader for Flipper Zero `.ir` code files."""

import asyncio
from functools import partial
from pathlib import Path

from .commands import Command, NECCommand

_DEFAULT_BASE_DIR = Path(__file__).parent / "codes"


class CommandCollection:
    """A collection of IR commands backed by a Flipper `.ir` file.

    The file is read and parsed lazily on the first `load_command` call —
    the blocking I/O is dispatched to the running loop's default executor.
    The parsed result is cached for subsequent calls.
    """

    __slots__ = ("_commands", "_path")

    def __init__(self, path: Path) -> None:
        """Initialize the collection with the resolved path to the `.ir` file."""
        self._path = path
        self._commands: dict[str, Command] | None = None

    async def load_commands(self) -> dict[str, Command]:
        """Return the full command mapping, parsing the file on first use."""
        commands = self._commands
        if commands is None:
            content = await asyncio.to_thread(
                partial(self._path.read_text, encoding="utf-8")
            )
            commands = parse_ir(content)
            self._commands = commands
        return commands

    async def load_command(self, name: str) -> Command:
        """Return the named command, parsing the backing file on first use."""
        commands = await self.load_commands()
        try:
            return commands[name]
        except KeyError:
            raise ValueError(f"No command named {name!r} in {self._path}") from None

    def __repr__(self) -> str:
        """Return the repr for the collection."""
        state = "loaded" if self._commands is not None else "not loaded"
        return f"CommandCollection(path={self._path!s}, {state})"


def load_codes(path: str, *, base_dir: Path | str | None = None) -> CommandCollection:
    """Return a `CommandCollection` for a Flipper `.ir` file.

    `path` is a relative path (without extension) under the base directory,
    e.g. ``"lg/tv"``. When `base_dir` is omitted, the packaged `codes`
    directory is used.

    The `.ir` file is not opened or parsed until
    `CommandCollection.load_command` is first awaited. The resolved path
    is validated eagerly to reject traversal outside the base directory.
    """
    base = Path(base_dir) if base_dir is not None else _DEFAULT_BASE_DIR
    resolved_base = base.resolve()
    ir_path = (base / f"{path}.ir").resolve()
    if not ir_path.is_relative_to(resolved_base):
        raise ValueError(
            f"Code path {path!r} resolves outside the base directory {base}"
        )
    return CommandCollection(ir_path)


def parse_ir(content: str) -> dict[str, Command]:
    """Parse Flipper `.ir` file content into a mapping of name to Command."""
    commands: dict[str, Command] = {}
    current: dict[str, str] = {}

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#"):
            _flush_record(current, commands)
            current = {}
            continue
        key, sep, value = line.partition(":")
        if not sep:
            continue
        current[key.strip().lower()] = value.strip()

    _flush_record(current, commands)
    return commands


def _flush_record(record: dict[str, str], commands: dict[str, Command]) -> None:
    """Convert a record dict into a Command and store it by name."""
    name = record.get("name")
    if name is None or "protocol" not in record:
        return
    if name in commands:
        raise ValueError(f"Duplicate command name: {name!r}")
    commands[name] = _build_command(record)


def _build_command(record: dict[str, str]) -> Command:
    """Build a Command from a parsed Flipper `.ir` record."""
    name = record["name"]
    protocol = record["protocol"].upper()
    if protocol == "NEC":
        address_bytes = _required_hex_bytes(record, "address", name, min_length=1)
        command_bytes = _required_hex_bytes(record, "command", name, min_length=1)
        return NECCommand(address=address_bytes[0], command=command_bytes[0])
    if protocol == "NECEXT":
        address_bytes = _required_hex_bytes(record, "address", name, min_length=2)
        command_bytes = _required_hex_bytes(record, "command", name, min_length=1)
        address = address_bytes[0] | (address_bytes[1] << 8)
        return NECCommand(address=address, command=command_bytes[0])
    raise ValueError(f"Unsupported protocol: {record['protocol']}")


def _required_hex_bytes(
    record: dict[str, str], field: str, name: str, *, min_length: int
) -> list[int]:
    """Parse a required hex-byte field, raising `ValueError` with context."""
    value = record.get(field)
    if value is None or not value.strip():
        raise ValueError(f"Command {name!r}: missing required field {field!r}")
    try:
        parsed = _parse_hex_bytes(value)
    except ValueError as exc:
        raise ValueError(
            f"Command {name!r}: invalid hex bytes in field {field!r}: {value!r}"
        ) from exc
    if len(parsed) < min_length:
        raise ValueError(
            f"Command {name!r}: field {field!r} needs at least "
            f"{min_length} byte(s), got {len(parsed)}"
        )
    return parsed


def _parse_hex_bytes(value: str) -> list[int]:
    """Parse a Flipper hex-byte string like ``04 FB 00 00`` into integers 0–255."""
    result: list[int] = []
    for token in value.split():
        byte = int(token, 16)
        if not 0 <= byte <= 0xFF:
            raise ValueError(f"Hex byte out of range: {token!r}")
        result.append(byte)
    return result

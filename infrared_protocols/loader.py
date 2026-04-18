"""Loader for Flipper Zero `.ir` code files."""

import asyncio
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

    async def load_command(self, name: str) -> Command:
        """Return the named command, parsing the backing file on first use."""
        commands = self._commands
        if commands is None:
            loop = asyncio.get_running_loop()
            commands = await loop.run_in_executor(
                None, _parse_ir_file, self._path
            )
            self._commands = commands
        try:
            return commands[name]
        except KeyError:
            raise ValueError(
                f"No command named {name!r} in {self._path}"
            ) from None

    def __repr__(self) -> str:
        """Return the repr for the collection."""
        state = "loaded" if self._commands is not None else "not loaded"
        return f"CommandCollection(path={self._path!s}, {state})"


def load_codes(
    path: str, *, base_dir: Path | str | None = None
) -> CommandCollection:
    """Return a `CommandCollection` for a Flipper `.ir` file.

    `path` is a relative path (without extension) under the base directory,
    e.g. ``"lg/tv"``. When `base_dir` is omitted, the packaged `codes`
    directory is used.

    This call performs no file I/O — the file is opened and parsed when
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


def _parse_ir_file(path: Path) -> dict[str, Command]:
    """Parse a Flipper `.ir` file into a mapping of name to Command."""
    commands: dict[str, Command] = {}
    current: dict[str, str] = {}

    with path.open(encoding="utf-8") as fh:
        for raw_line in fh:
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
    commands[name] = _build_command(record)


def _build_command(record: dict[str, str]) -> Command:
    """Build a Command from a parsed Flipper `.ir` record."""
    protocol = record["protocol"].upper()
    if protocol in ("NEC", "NECEXT"):
        address_bytes = _parse_hex_bytes(record["address"])
        command_bytes = _parse_hex_bytes(record["command"])
        if protocol == "NEC":
            address = address_bytes[0]
        else:
            address = address_bytes[0] | (address_bytes[1] << 8)
        return NECCommand(address=address, command=command_bytes[0])
    raise ValueError(f"Unsupported protocol: {record['protocol']}")


def _parse_hex_bytes(value: str) -> list[int]:
    """Parse a Flipper hex-byte string like ``04 FB 00 00`` into integers."""
    return [int(token, 16) for token in value.split()]

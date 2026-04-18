"""Tests for the Flipper `.ir` loader."""

import asyncio
from pathlib import Path

import pytest

from infrared_protocols import Command, NECCommand, get_codes, parse_ir

_BUNDLED_CODES_DIR = Path(__file__).resolve().parent.parent / (
    "infrared_protocols/codes"
)


def test_get_codes_lg_tv() -> None:
    """Test loading bundled LG TV codes (NECext address)."""
    codes = get_codes("lg/tv")
    power = asyncio.run(codes.load_command("POWER"))
    assert isinstance(power, NECCommand)
    assert power.address == 0xFB04
    assert power.command == 0x08
    assert power.modulation == 38000
    assert power.repeat_count == 0

    volume_up = asyncio.run(codes.load_command("VOLUME_UP"))
    assert volume_up.command == 0x02


def test_get_codes_nedis() -> None:
    """Test loading bundled Nedis codes (plain NEC address)."""
    codes = get_codes("nedis/vmat3462at")
    power = asyncio.run(codes.load_command("POWER"))
    assert isinstance(power, NECCommand)
    assert power.address == 0x00
    assert power.command == 0x14


def test_load_command_unknown() -> None:
    """Test that unknown commands raise ValueError."""
    codes = get_codes("lg/tv")
    with pytest.raises(ValueError, match="No command named"):
        asyncio.run(codes.load_command("NOT_A_REAL_COMMAND"))


def test_get_codes_base_dir_override(tmp_path: Path) -> None:
    """Test loading from a custom base directory."""
    ir_file = tmp_path / "device.ir"
    ir_file.write_text(
        """Filetype: IR signals file
Version: 1
#
name: POWER
type: parsed
protocol: NEC
address: 04 00 00 00
command: 08 00 00 00
#
name: VOL_UP
type: parsed
protocol: NECext
address: 04 FB 00 00
command: 02 00 00 00
"""
    )

    codes = get_codes("device", base_dir=tmp_path)
    power = asyncio.run(codes.load_command("POWER"))
    vol_up = asyncio.run(codes.load_command("VOL_UP"))
    assert power.address == 0x04
    assert power.command == 0x08
    assert vol_up.address == 0xFB04
    assert vol_up.command == 0x02


def test_get_codes_rejects_path_traversal(tmp_path: Path) -> None:
    """Test that paths escaping the base directory are rejected."""
    (tmp_path / "outside.ir").write_text(
        "Filetype: IR signals file\nVersion: 1\n"
    )
    inner = tmp_path / "inner"
    inner.mkdir()

    with pytest.raises(ValueError, match="outside the base directory"):
        get_codes("../outside", base_dir=inner)


def test_get_codes_rejects_absolute_path(tmp_path: Path) -> None:
    """Test that absolute paths are rejected."""
    (tmp_path / "elsewhere.ir").write_text(
        "Filetype: IR signals file\nVersion: 1\n"
    )
    base = tmp_path / "base"
    base.mkdir()

    with pytest.raises(ValueError, match="outside the base directory"):
        get_codes(str(tmp_path / "elsewhere"), base_dir=base)


def test_get_codes_is_lazy(tmp_path: Path) -> None:
    """Test that the `.ir` file is not opened until load_command is awaited."""
    ir_path = tmp_path / "dev.ir"
    codes = get_codes("dev", base_dir=tmp_path)

    ir_path.write_text(
        """Filetype: IR signals file
Version: 1
#
name: POWER
type: parsed
protocol: NEC
address: 04 00 00 00
command: 08 00 00 00
"""
    )

    power = asyncio.run(codes.load_command("POWER"))
    assert power.command == 0x08


def test_load_command_caches_parsed_file(tmp_path: Path) -> None:
    """Test that the `.ir` file is parsed only once across calls."""
    ir_path = tmp_path / "dev.ir"
    ir_path.write_text(
        """Filetype: IR signals file
Version: 1
#
name: POWER
type: parsed
protocol: NEC
address: 04 00 00 00
command: 08 00 00 00
"""
    )
    codes = get_codes("dev", base_dir=tmp_path)

    async def load_twice_then_delete_file() -> tuple[Command, Command]:
        first = await codes.load_command("POWER")
        ir_path.unlink()
        second = await codes.load_command("POWER")
        return first, second

    first, second = asyncio.run(load_twice_then_delete_file())
    assert first is second


def test_load_all_bundled_codes() -> None:
    """Load every bundled `.ir` file and fetch a command from each."""
    ir_files = sorted(_BUNDLED_CODES_DIR.rglob("*.ir"))
    assert ir_files, "expected at least one bundled .ir file"

    async def load_first_command(ir_file: Path) -> Command:
        relative = ir_file.relative_to(_BUNDLED_CODES_DIR).with_suffix("")
        codes = get_codes(str(relative))
        first_name = _first_command_name(ir_file)
        return await codes.load_command(first_name)

    for ir_file in ir_files:
        command = asyncio.run(load_first_command(ir_file))
        assert isinstance(command, Command)


def test_load_commands_returns_full_mapping() -> None:
    """Test that load_commands returns every command in the file."""
    codes = get_codes("nedis/vmat3462at")
    commands = asyncio.run(codes.load_commands())
    assert set(commands) == {
        "POWER",
        "A_OFF",
        "A_1",
        "A_2",
        "A_3",
        "A_4",
        "B_OFF",
        "B_1",
        "B_2",
        "B_3",
        "B_4",
    }
    assert commands["POWER"].command == 0x14


def test_load_commands_shares_cache_with_load_command(tmp_path: Path) -> None:
    """Test that load_commands and load_command share the parsed cache."""
    ir_path = tmp_path / "dev.ir"
    ir_path.write_text(
        """Filetype: IR signals file
Version: 1
#
name: POWER
type: parsed
protocol: NEC
address: 04 00 00 00
command: 08 00 00 00
"""
    )
    codes = get_codes("dev", base_dir=tmp_path)

    async def load_both_then_delete_file() -> tuple[Command, Command]:
        via_all = (await codes.load_commands())["POWER"]
        ir_path.unlink()
        via_one = await codes.load_command("POWER")
        return via_all, via_one

    via_all, via_one = asyncio.run(load_both_then_delete_file())
    assert via_all is via_one


def test_parse_ir_from_string() -> None:
    """Test that parse_ir parses `.ir` file content directly."""
    content = """Filetype: IR signals file
Version: 1
#
name: POWER
type: parsed
protocol: NEC
address: 04 00 00 00
command: 08 00 00 00
#
name: VOL_UP
type: parsed
protocol: NECext
address: 04 FB 00 00
command: 02 00 00 00
"""

    commands = parse_ir(content)
    assert isinstance(commands["POWER"], NECCommand)
    assert commands["POWER"].address == 0x04
    assert commands["POWER"].command == 0x08
    assert commands["VOL_UP"].address == 0xFB04
    assert commands["VOL_UP"].command == 0x02


def test_get_codes_duplicate_name(tmp_path: Path) -> None:
    """Test that duplicate command names raise ValueError."""
    ir_file = tmp_path / "dup.ir"
    ir_file.write_text(
        """Filetype: IR signals file
Version: 1
#
name: POWER
type: parsed
protocol: NEC
address: 04 00 00 00
command: 08 00 00 00
#
name: POWER
type: parsed
protocol: NEC
address: 04 00 00 00
command: 09 00 00 00
"""
    )
    codes = get_codes("dup", base_dir=tmp_path)
    with pytest.raises(ValueError, match="Duplicate command name"):
        asyncio.run(codes.load_commands())


def test_get_codes_missing_address(tmp_path: Path) -> None:
    """Test that a missing required field raises a descriptive ValueError."""
    ir_file = tmp_path / "bad.ir"
    ir_file.write_text(
        """Filetype: IR signals file
Version: 1
#
name: POWER
type: parsed
protocol: NEC
command: 08 00 00 00
"""
    )
    codes = get_codes("bad", base_dir=tmp_path)
    with pytest.raises(ValueError, match="Command 'POWER'.*'address'"):
        asyncio.run(codes.load_commands())


def test_get_codes_necext_truncated_address(tmp_path: Path) -> None:
    """Test that NECext with a single address byte raises ValueError."""
    ir_file = tmp_path / "bad.ir"
    ir_file.write_text(
        """Filetype: IR signals file
Version: 1
#
name: POWER
type: parsed
protocol: NECext
address: 04
command: 08 00 00 00
"""
    )
    codes = get_codes("bad", base_dir=tmp_path)
    with pytest.raises(ValueError, match="at least 2 byte"):
        asyncio.run(codes.load_commands())


def test_get_codes_unsupported_protocol(tmp_path: Path) -> None:
    """Test that unsupported protocols raise ValueError on access."""
    ir_file = tmp_path / "bad.ir"
    ir_file.write_text(
        """Filetype: IR signals file
Version: 1
#
name: FOO
type: parsed
protocol: RC5
address: 01 00 00 00
command: 02 00 00 00
"""
    )
    codes = get_codes("bad", base_dir=tmp_path)
    with pytest.raises(ValueError, match="Unsupported protocol"):
        asyncio.run(codes.load_command("FOO"))


def _first_command_name(ir_file: Path) -> str:
    """Return the first ``name:`` entry in a `.ir` file."""
    for line in ir_file.read_text(encoding="utf-8").splitlines():
        key, sep, value = line.partition(":")
        if sep and key.strip().lower() == "name":
            return value.strip()
    raise AssertionError(f"{ir_file} has no named commands")

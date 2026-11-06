"""Physical captures recorded by Arduino-IRremote and IRremoteESP8266."""

import json
from collections.abc import Callable
from pathlib import Path

import pytest

from infrared_protocols.commands.climate import ClimateFan, ClimateMode, ClimateState
from infrared_protocols.commands.kaseikyo import KaseikyoCommand
from infrared_protocols.commands.marantz_extended import MarantzExtendedCommand
from infrared_protocols.commands.rc5 import RC5Command
from infrared_protocols.commands.rc6 import RC6Command
from infrared_protocols.commands.remko_ar715 import RemkoAr715Command

_CAPTURES = json.loads(
    (Path(__file__).parents[1] / "fixtures/receiver_captures.json").read_text()
)["captures"]


@pytest.mark.parametrize(
    "raw,address,command,toggle,decoder",
    [
        pytest.param(
            c["timings"],
            c["address"],
            c["command"],
            c["toggle"],
            {"rc5": RC5Command.from_raw_timings, "rc6": RC6Command.from_raw_timings}[
                c["protocol"]
            ],
            id=f"{c['protocol']}-{c['address']:x}-{c['command']:x}",
        )
        for c in _CAPTURES
        if c["protocol"] in ("rc5", "rc6")
    ],
)
def test_recorded_biphase(
    raw: list[int],
    address: int,
    command: int,
    toggle: int,
    decoder: Callable[[list[int]], RC5Command | RC6Command | None],
) -> None:
    """Decode measured edges and the independently recorded toggle bit."""
    result = decoder(raw)
    assert result is not None
    assert (result.address, result.command, result.toggle) == (address, command, toggle)


@pytest.mark.parametrize(
    "raw,address,command,toggle,extension",
    [
        pytest.param(
            c["timings"],
            c["address"],
            c["command"],
            c["toggle"],
            c["extension"],
            id=f"marantz-{c['address']:x}-{c['command']:x}",
        )
        for c in _CAPTURES
        if c["protocol"] == "marantz"
    ],
)
def test_recorded_marantz(
    raw: list[int], address: int, command: int, toggle: int, extension: int
) -> None:
    """The extended frame retains its command and extension after the long pause."""
    result = MarantzExtendedCommand.from_raw_timings(raw)
    assert result is not None
    assert (result.address, result.command, result.toggle, result.extension) == (
        address,
        command,
        toggle,
        extension,
    )


@pytest.mark.parametrize(
    "raw",
    [
        pytest.param(c["timings"], id=f"rc6a-{i}")
        for i, c in enumerate(_CAPTURES)
        if c["protocol"] == "rc6a"
    ],
)
def test_unsupported_rc6a(raw: list[int]) -> None:
    """The fixed 20-bit RC6 decoder cannot silently truncate a longer RC6A word."""
    assert RC6Command.from_raw_timings(raw) is None


def test_recorded_kaseikyo() -> None:
    """The Panasonic capture preserves its manufacturer and application bytes."""
    capture = next(c for c in _CAPTURES if c["protocol"] == "kaseikyo")
    result = KaseikyoCommand.from_raw_timings(capture["timings"])
    assert result is not None
    assert result.address == 0x2002
    assert result.data == bytes.fromhex("10ff7699")


def test_recorded_remko() -> None:
    """The handheld remote adds a final mark after its 3.5-ms footer space."""
    capture = next(c for c in _CAPTURES if c["protocol"] == "remko")
    result = RemkoAr715Command.from_raw_timings(capture["timings"])
    assert result is not None
    assert result.data == 0x8000000058802
    assert result.state == ClimateState(
        power=False,
        mode=ClimateMode.COOL,
        temperature=16,
        fan=ClimateFan.HIGH,
        swing_v=True,
    )

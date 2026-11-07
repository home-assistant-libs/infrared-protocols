"""Tests for LG and LG2 raw transports."""

import pytest

from infrared_protocols.commands.lg import Lg28Command, Lg32Command
from infrared_protocols.commands.lg_ac import LgAcCommand, LgAcMode


def test_lg2_roundtrip() -> None:
    """Learned LG2 packets retain their leader and 550-us marks."""
    raw = LgAcCommand(mode=LgAcMode.COOL, temperature=24).get_raw_timings()
    received = Lg28Command.from_raw_timings(raw)
    assert received is not None
    assert received.lg2 is True
    assert received.get_raw_timings() == raw
    assert Lg32Command.from_raw_timings(raw) is None


@pytest.mark.parametrize(
    "command",
    [
        pytest.param(Lg28Command(data=0x88C0051, repeat_count=2), id="lg28"),
        pytest.param(Lg28Command(data=0x88C0051, lg2=True, repeat_count=2), id="lg2"),
        pytest.param(Lg32Command(data=0xABCDEFAB, repeat_count=2), id="lg32"),
    ],
)
def test_lg_repeat_codes(command: Lg28Command | Lg32Command) -> None:
    """A complete learned command includes its trailing held-key repeat count."""
    received = type(command).from_raw_timings(command.get_raw_timings())
    assert received is not None
    assert (received.data, received.repeat_count) == (command.data, 2)
    assert received.get_raw_timings() == command.get_raw_timings()


def test_lg_independent_repeat_code() -> None:
    """The protocol's short repeat is not treated as unexpected trailing data."""
    first = Lg28Command(data=0x88C0051).get_raw_timings()
    result = Lg28Command.from_raw_timings(first + [-39750, 8500, -2250, 550])
    assert result is not None
    assert (result.data, result.repeat_count) == (0x88C0051, 1)


@pytest.mark.parametrize(
    "command",
    [
        pytest.param(Lg28Command(data=0x88C0051, repeat_count=2), id="lg28"),
        pytest.param(Lg28Command(data=0x88C0051, lg2=True, repeat_count=2), id="lg2"),
        pytest.param(Lg32Command(data=0xABCDEFAB, repeat_count=2), id="lg32"),
    ],
)
@pytest.mark.parametrize("trim", [1, 2])
def test_clipped_last_repeat(command: Lg28Command | Lg32Command, trim: int) -> None:
    """A clipped last repeat code does not discard a complete learned word."""
    result = type(command).from_raw_timings(command.get_raw_timings()[:-trim])
    assert result is not None
    assert (result.data, result.repeat_count) == (command.data, 1)


def test_lg32_repeat_mark() -> None:
    """The 32-bit format uses the specified 8950-us repeat leader."""
    command = Lg32Command(data=0xABCDEFAB, repeat_count=1)
    assert command.get_raw_timings()[-3:] == [8950, -2250, 550]


def test_clipped_intermediate_repeat_rejected() -> None:
    """A malformed repeat before another full repeat invalidates the capture."""
    raw = Lg28Command(data=0x88C0051, repeat_count=2).get_raw_timings()
    del raw[-5]
    assert Lg28Command.from_raw_timings(raw) is None


@pytest.mark.parametrize("gap", [-10000, -200000], ids=["too-short", "too-long"])
def test_repeat_cadence(gap: int) -> None:
    """A short repeat code outside its held-key cadence is not counted."""
    raw = Lg28Command(data=0x88C0051, repeat_count=1).get_raw_timings()
    raw[-4] = gap
    assert Lg28Command.from_raw_timings(raw) is None

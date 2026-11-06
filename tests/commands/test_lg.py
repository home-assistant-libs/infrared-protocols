"""Tests for lg2 protocol behavior."""

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
        Lg28Command(data=0x88C0051, repeat_count=2),
        Lg28Command(data=0x88C0051, lg2=True, repeat_count=2),
        Lg32Command(data=0xABCDEFAB, repeat_count=2),
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

"""Tests for zhlt01 protocol behavior."""

import pytest

from infrared_protocols.commands.climate import ClimateFan, ClimateMode
from infrared_protocols.commands.zhlt01 import Zhlt01Command


@pytest.mark.parametrize(
    "boost,fan,expected",
    [
        (True, ClimateFan.LOW, ClimateFan.HIGH),
        (False, ClimateFan.QUIET, ClimateFan.QUIET),
    ],
)
def test_zhlt_boost_and_quiet(
    boost: bool, fan: ClimateFan, expected: ClimateFan
) -> None:
    """Boost overrides speed while quiet retains the dedicated low-bit code."""
    sent = Zhlt01Command(mode=ClimateMode.COOL, temperature=24, fan=fan, boost=boost)
    received = Zhlt01Command.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.boost == boost
    assert received.state.fan == expected


def test_natural_wind_moves_vane() -> None:
    """A natural-wind vane setting is motion, not a fixed position."""
    sent = Zhlt01Command(mode=ClimateMode.COOL, temperature=24)
    data = bytearray(sent.data)
    data[7] = 0x12
    data[6] = data[7] ^ 255
    sent.data = bytes(data)
    result = Zhlt01Command.from_raw_timings(sent.get_raw_timings())
    assert result is not None
    assert result.state.swing_v is True

"""Tests for zhlt01 protocol behavior."""

import pytest

from infrared_protocols.commands.zhlt01 import Zhlt01Command, Zhlt01FanSpeed, Zhlt01Mode


@pytest.mark.parametrize(
    "boost,fan,expected",
    [
        pytest.param(True, Zhlt01FanSpeed.LOW, Zhlt01FanSpeed.HIGH, id="boost"),
        pytest.param(False, Zhlt01FanSpeed.QUIET, Zhlt01FanSpeed.QUIET, id="quiet"),
    ],
)
def test_zhlt_boost_and_quiet(
    boost: bool, fan: Zhlt01FanSpeed, expected: Zhlt01FanSpeed
) -> None:
    """Boost overrides speed while quiet retains the dedicated low-bit code."""
    sent = Zhlt01Command(mode=Zhlt01Mode.COOL, temperature=24, fan=fan, boost=boost)
    received = Zhlt01Command.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.boost == boost
    assert received.state.fan == expected


def test_natural_wind_moves_vane() -> None:
    """A natural-wind vane setting is motion, not a fixed position."""
    sent = Zhlt01Command(mode=Zhlt01Mode.COOL, temperature=24)
    data = bytearray(sent.data)
    data[7] = 0x12
    data[6] = data[7] ^ 255
    sent.data = bytes(data)
    result = Zhlt01Command.from_raw_timings(sent.get_raw_timings())
    assert result is not None
    assert result.state.swing_v is True

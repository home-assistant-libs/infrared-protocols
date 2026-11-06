"""Complete presses delivered as multiple default receiver captures."""

import pytest

from infrared_protocols.commands._climate import ClimatePacket
from infrared_protocols.commands._split_climate import SplitClimateCommand
from infrared_protocols.commands.climate import ClimateMode
from infrared_protocols.commands.daikin_arc import DaikinArcCommand
from infrared_protocols.commands.daikin_brc import DaikinBrcCommand
from infrared_protocols.commands.emmeti import EmmetiCommand
from infrared_protocols.commands.noblex import NoblexCommand
from infrared_protocols.commands.pd_pioneer_climate import PdPioneerClimateCommand


def _captures(raw: list[int]) -> list[list[int]]:
    """Model a receiver which reports a ten-millisecond final idle timeout."""
    result: list[list[int]] = []
    start = 0
    for index, duration in enumerate(raw):
        if duration <= -10000:
            result.append(raw[start:index] + [-10000])
            start = index + 1
    if start < len(raw):
        result.append(raw[start:] + [-10000])
    return result


@pytest.mark.parametrize(
    "command",
    [
        pytest.param(
            DaikinArcCommand(mode=ClimateMode.COOL, temperature=24),
            id="arc-three-bursts",
        ),
        pytest.param(DaikinBrcCommand(mode=ClimateMode.COOL, temperature=24), id="brc"),
        pytest.param(EmmetiCommand(mode=ClimateMode.COOL, temperature=24), id="emmeti"),
        pytest.param(NoblexCommand(mode=ClimateMode.COOL, temperature=24), id="noblex"),
        pytest.param(
            PdPioneerClimateCommand(mode=ClimateMode.COOL, temperature=24),
            id="pd-pioneer",
        ),
    ],
)
def test_default_receiver_captures(
    command: ClimatePacket | SplitClimateCommand,
) -> None:
    """Validate the complete press without requiring a longer receiver timeout."""
    captures = _captures(command.get_raw_timings())
    received = type(command).from_raw_captures(captures)
    assert received is not None
    assert received.state == command.state
    assert received.get_raw_timings() == command.get_raw_timings()
    assert type(command).from_raw_captures(captures[:-1]) is None
    captures[-1][0] = 0
    assert type(command).from_raw_captures(captures) is None

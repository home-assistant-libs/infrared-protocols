"""Complete presses delivered as multiple default receiver captures."""

import pytest

from infrared_protocols.commands._climate import ClimatePacket
from infrared_protocols.commands._split_climate import SplitClimateCommand
from infrared_protocols.commands.climate import ClimateMode
from infrared_protocols.commands.daikin_arc import DaikinArcCommand
from infrared_protocols.commands.daikin_brc import DaikinBrcCommand
from infrared_protocols.commands.emmeti import EmmetiCommand
from infrared_protocols.commands.friedrich import (
    FriedrichButton,
    FriedrichCommand,
    FriedrichUtilityCommand,
)
from infrared_protocols.commands.mistral import MistralCommand
from infrared_protocols.commands.mitsubishi import MitsubishiCommand
from infrared_protocols.commands.noblex import NoblexCommand
from infrared_protocols.commands.pd_pioneer_climate import PdPioneerClimateCommand


def _captures(raw: list[int], *, idle: int = 10000) -> list[list[int]]:
    """Model a receiver which reports its configured final idle timeout."""
    result: list[list[int]] = []
    start = 0
    for index, duration in enumerate(raw):
        if duration <= -idle:
            result.append(raw[start:index] + [-idle])
            start = index + 1
    if start < len(raw):
        body = raw[start:]
        if body[-1] < 0:
            body = body[:-1]
        result.append(body + [-idle])
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
            MistralCommand(mode=ClimateMode.COOL, temperature=24), id="mistral"
        ),
        pytest.param(
            FriedrichCommand(mode=ClimateMode.COOL, temperature_f=72), id="friedrich"
        ),
        pytest.param(
            FriedrichUtilityCommand(button=FriedrichButton.POWER_OFF),
            id="friedrich-off",
        ),
        pytest.param(
            PdPioneerClimateCommand(mode=ClimateMode.COOL, temperature=24),
            id="pd-pioneer",
        ),
    ],
)
@pytest.mark.parametrize("idle", [5000, 10000, 20000, 30000, 40000])
def test_default_receiver_captures(
    command: ClimatePacket | SplitClimateCommand,
    idle: int,
) -> None:
    """Validate the complete press without requiring a longer receiver timeout."""
    captures = _captures(command.get_raw_timings(), idle=idle)
    received = type(command).from_raw_captures(captures, idle=idle)
    assert received is not None
    assert received.state == command.state
    assert received.get_raw_timings() == command.get_raw_timings()
    assert (
        type(command).from_raw_captures([command.get_raw_timings()], idle=idle)
        is not None
    )
    assert type(command).from_raw_captures(captures[:-1], idle=idle) is None
    captures[-1][0] = 0
    assert type(command).from_raw_captures(captures, idle=idle) is None


@pytest.mark.parametrize("cls", [DaikinArcCommand, NoblexCommand])
def test_receiver_idle_too_short(
    cls: type[ClimatePacket] | type[SplitClimateCommand],
) -> None:
    """An idle timeout below the supported framing floor is rejected."""
    with pytest.raises(ValueError, match="idle must be at least"):
        cls.from_raw_captures([], idle=2999)


@pytest.mark.parametrize(
    "copies", [pytest.param(1, id="single"), pytest.param(2, id="both")]
)
@pytest.mark.parametrize("idle", [10000, 20000])
def test_mitsubishi_copies(copies: int, idle: int) -> None:
    """Accept one complete copy or both, including captures spanning the copy gap."""
    command = MitsubishiCommand(mode=ClimateMode.COOL, temperature=24)
    raw = command.get_raw_timings()
    copy = raw[: raw.index(-17500)]
    transmitted = (copy + [-17500]) * (copies - 1) + copy
    received = MitsubishiCommand.from_raw_captures(
        _captures(transmitted, idle=idle), idle=idle
    )
    assert received is not None
    assert received.state == command.state
    assert received.get_raw_timings() == raw


def test_mitsubishi_conflicting_captures() -> None:
    """A second valid packet with different settings invalidates the whole press."""
    first = MitsubishiCommand(mode=ClimateMode.COOL, temperature=24)
    second = MitsubishiCommand(mode=ClimateMode.COOL, temperature=25)
    captures = [
        _captures(first.get_raw_timings())[0],
        _captures(second.get_raw_timings())[0],
    ]
    assert MitsubishiCommand.from_raw_captures(captures) is None

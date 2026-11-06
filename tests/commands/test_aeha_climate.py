"""Tests for complete AEHA climate captures."""

import pytest

from infrared_protocols.commands._aeha_climate import AehaClimatePacket
from infrared_protocols.commands.climate import ClimateMode
from infrared_protocols.commands.friedrich import (
    FriedrichButton,
    FriedrichCommand,
    FriedrichUtilityCommand,
)
from infrared_protocols.commands.mistral import MistralCommand


@pytest.fixture(
    params=[
        pytest.param(
            FriedrichCommand(mode=ClimateMode.COOL, temperature_f=72),
            id="friedrich",
        ),
        pytest.param(
            FriedrichUtilityCommand(button=FriedrichButton.POWER_OFF),
            id="friedrich-utility",
        ),
        pytest.param(
            MistralCommand(mode=ClimateMode.COOL, temperature=22),
            id="mistral",
        ),
    ],
)
def command(request: pytest.FixtureRequest) -> AehaClimatePacket:
    """Return each climate family using the AEHA transport."""
    assert isinstance(request.param, AehaClimatePacket)
    return request.param


@pytest.mark.parametrize(
    "tail",
    [
        pytest.param([], id="last-mark"),
        pytest.param([-8000], id="trailer"),
        pytest.param([-20000], id="receiver-idle"),
    ],
)
def test_complete_capture(command: AehaClimatePacket, tail: list[int]) -> None:
    """One complete climate frame accepts an optional trailing idle space."""
    received = type(command).from_raw_timings(command.get_raw_timings() + tail)
    assert received is not None
    assert received.data == command.data


@pytest.mark.parametrize(
    "tail",
    [
        pytest.param([-20000, 9000, -4500, 560, -560, 560], id="foreign-burst"),
        pytest.param([-20000, 425], id="stray-mark"),
    ],
)
def test_trailing_pulses_rejected(command: AehaClimatePacket, tail: list[int]) -> None:
    """The climate packet must consume the capture, including after its trailer."""
    assert type(command).from_raw_timings(command.get_raw_timings() + tail) is None

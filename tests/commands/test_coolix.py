"""Tests for coolix protocol behavior."""

from itertools import product

import pytest

from infrared_protocols.codes.coolix.climate import CoolixCode
from infrared_protocols.commands.climate import ClimateFan, ClimateMode, ClimateState
from infrared_protocols.commands.coolix import CoolixCommand


@pytest.mark.parametrize(
    "mode,temperature,expected,fan",
    [
        pytest.param(
            mode,
            temp,
            None if mode == ClimateMode.FAN_ONLY else temp,
            fan,
            id=f"{mode}-{temp}-{fan}",
        )
        for mode, temp, fan in product(
            ClimateMode,
            [17, 24, 30],
            [ClimateFan.AUTO, ClimateFan.LOW, ClimateFan.MEDIUM, ClimateFan.HIGH],
        )
        if fan == ClimateFan.AUTO or mode not in (ClimateMode.AUTO, ClimateMode.DRY)
    ],
)
def test_coolix_state(
    mode: ClimateMode, temperature: int, expected: int | None, fan: ClimateFan
) -> None:
    """Fan-only has no set point; other modes recover the requested state."""
    command = CoolixCommand.climate(mode=mode, temperature=temperature, fan=fan)
    result = CoolixCommand.from_raw_timings(command.get_raw_timings())
    assert result is not None
    assert result.state == ClimateState(
        power=True,
        mode=mode,
        fan=fan,
        temperature=expected,
    )


@pytest.mark.parametrize("code", list(CoolixCode))
def test_coolix_buttons(code: CoolixCode) -> None:
    """Known button actions retain their complete command word."""
    command = code.to_command()
    result = CoolixCommand.from_raw_timings(command.get_raw_timings())
    assert result is not None
    assert result.first == code.value


@pytest.mark.parametrize(
    "mode,temperature,fan,word",
    [
        pytest.param(ClimateMode.COOL, 24, ClimateFan.LOW, 0xB29F40, id="cool24-low"),
        pytest.param(ClimateMode.HEAT, 30, ClimateFan.HIGH, 0xB23FBC, id="heat30-high"),
    ],
)
def test_coolix_control_bytes(
    mode: ClimateMode, temperature: int, fan: ClimateFan, word: int
) -> None:
    """The three-byte word is verified independently of the round trip."""
    assert (
        CoolixCommand.climate(mode=mode, temperature=temperature, fan=fan).first == word
    )


@pytest.mark.parametrize("code", list(CoolixCode))
def test_coolix_action_copies(code: CoolixCode) -> None:
    """Named actions include the protocol's second identical packet."""
    sent = code.to_command()
    assert sent.first == sent.second == code
    assert sent.get_raw_timings().count(-5600) == 1


def test_coolix_unknown_state() -> None:
    """Unknown raw control fields remain raw data without raising on state access."""
    sent = CoolixCommand(first=0xB2FFF0)
    assert sent.state is None

"""Tests for coolix protocol behavior."""

from itertools import product

import pytest

from infrared_protocols.commands.coolix import (
    CoolixCommand,
    CoolixFanSpeed,
    CoolixMode,
    CoolixState,
)


@pytest.mark.parametrize(
    "mode,temperature,expected,fan",
    [
        pytest.param(
            mode,
            temp,
            None if mode == CoolixMode.FAN_ONLY else temp,
            fan,
            id=f"{mode}-{temp}-{fan}",
        )
        for mode, temp, fan in product(
            CoolixMode,
            [17, 24, 30],
            [
                CoolixFanSpeed.AUTO,
                CoolixFanSpeed.LOW,
                CoolixFanSpeed.MEDIUM,
                CoolixFanSpeed.HIGH,
            ],
        )
        if fan == CoolixFanSpeed.AUTO or mode not in (CoolixMode.AUTO, CoolixMode.DRY)
    ],
)
def test_coolix_state(
    mode: CoolixMode, temperature: int, expected: int | None, fan: CoolixFanSpeed
) -> None:
    """Fan-only has no set point; other modes recover the requested state."""
    command = CoolixCommand.climate(mode=mode, temperature=temperature, fan=fan)
    result = CoolixCommand.from_raw_timings(command.get_raw_timings())
    assert result is not None
    assert result.state == CoolixState(
        power=True,
        mode=mode,
        fan=fan,
        temperature=expected,
    )


@pytest.mark.parametrize(
    "mode,temperature,fan,word",
    [
        pytest.param(
            CoolixMode.COOL, 24, CoolixFanSpeed.LOW, 0xB29F40, id="cool24-low"
        ),
        pytest.param(
            CoolixMode.HEAT, 30, CoolixFanSpeed.HIGH, 0xB23FBC, id="heat30-high"
        ),
        pytest.param(
            CoolixMode.COOL, 17, CoolixFanSpeed.MEDIUM, 0xB25F00, id="cool17-medium"
        ),
        pytest.param(
            CoolixMode.COOL, 24, CoolixFanSpeed.AUTO, 0xB2BF40, id="cool24-auto"
        ),
        pytest.param(CoolixMode.AUTO, 24, CoolixFanSpeed.AUTO, 0xB21F48, id="auto24"),
        pytest.param(CoolixMode.DRY, 24, CoolixFanSpeed.AUTO, 0xB21F44, id="dry24"),
        pytest.param(
            CoolixMode.FAN_ONLY, 24, CoolixFanSpeed.AUTO, 0xB2BFE4, id="fan-only"
        ),
    ],
)
def test_coolix_control_bytes(
    mode: CoolixMode, temperature: int, fan: CoolixFanSpeed, word: int
) -> None:
    """The three-byte word is verified independently of the round trip."""
    command = CoolixCommand.climate(mode=mode, temperature=temperature, fan=fan)
    assert command.first == command.second == word


def test_coolix_unknown_state() -> None:
    """Unknown raw control fields remain raw data without raising on state access."""
    sent = CoolixCommand(first=0xB2FFF0)
    assert sent.state is None

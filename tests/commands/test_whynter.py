"""Tests for whynter protocol behavior."""

import pytest

from infrared_protocols.commands.whynter import WhynterCommand, WhynterMode


@pytest.mark.parametrize(
    "temperature,is_fahrenheit",
    [
        pytest.param(16, False, id="c-min"),
        pytest.param(32, False, id="c-max"),
        pytest.param(61, True, id="f-min"),
        pytest.param(75, True, id="f-normal"),
        pytest.param(89, True, id="f-max"),
    ],
)
@pytest.mark.parametrize("power", [False, True], ids=["off", "on"])
def test_whynter_native_units(
    temperature: int, is_fahrenheit: bool, power: bool
) -> None:
    """Native units and set points survive decoding without rounding."""
    sent = WhynterCommand(
        mode=WhynterMode.COOL,
        temperature=temperature,
        is_fahrenheit=is_fahrenheit,
        power=power,
    )
    received = WhynterCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.state.is_fahrenheit is is_fahrenheit
    assert received.state.temperature == temperature
    state = received.state
    assert state.temperature is not None
    rebuilt = WhynterCommand(
        mode=state.mode,
        temperature=state.temperature,
        power=power,
        is_fahrenheit=state.is_fahrenheit,
    )
    assert rebuilt.get_raw_timings() == sent.get_raw_timings()

"""Tests for the generic E27 fan light remote codes."""

import pytest

from infrared_protocols.codes.generic.e27_fan_light import E27FanLightCode
from infrared_protocols.commands.nec import NECCommand


@pytest.mark.parametrize(
    ("code", "command"),
    [
        pytest.param(E27FanLightCode.FAN_TOGGLE, 0x09, id="fan_toggle"),
        pytest.param(E27FanLightCode.FAN_LOW, 0x03, id="fan_low"),
        pytest.param(E27FanLightCode.FAN_MEDIUM, 0x07, id="fan_medium"),
        pytest.param(E27FanLightCode.FAN_HIGH, 0x0B, id="fan_high"),
        pytest.param(E27FanLightCode.LIGHT_TOGGLE, 0x01, id="light_toggle"),
        pytest.param(
            E27FanLightCode.LIGHT_BRIGHTNESS_UP, 0x0A, id="light_brightness_up"
        ),
        pytest.param(
            E27FanLightCode.LIGHT_BRIGHTNESS_DOWN,
            0x02,
            id="light_brightness_down",
        ),
        pytest.param(E27FanLightCode.LIGHT_COLOR_WARMER, 0x05, id="light_color_warmer"),
        pytest.param(E27FanLightCode.LIGHT_COLOR_COOLER, 0x04, id="light_color_cooler"),
    ],
)
def test_e27_fan_light_builds_nec_command(code: E27FanLightCode, command: int) -> None:
    """Every code is an NEC command on the shared address."""
    built = code.to_command()
    assert isinstance(built, NECCommand)
    assert built.address == 0xFE01
    assert built.command == command
    assert built.subfunction is None


@pytest.mark.parametrize("repeat_count", [0, 1, 2])
def test_e27_fan_light_forwards_repeat_count(repeat_count: int) -> None:
    """The repeat count is forwarded to the NEC command."""
    built = E27FanLightCode.FAN_TOGGLE.to_command(repeat_count=repeat_count)
    assert isinstance(built, NECCommand)
    assert built.repeat_count == repeat_count


def test_e27_fan_light_round_trips_through_the_decoder() -> None:
    """Every code must decode back to itself from its own timings."""
    for code in E27FanLightCode:
        decoded = NECCommand.from_raw_timings(code.to_command().get_raw_timings())
        assert decoded is not None
        assert decoded.address == 0xFE01
        assert decoded.command == code.value

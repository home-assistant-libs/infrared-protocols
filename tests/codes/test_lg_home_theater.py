"""Tests for the LG home theater command codes."""

import pytest

from infrared_protocols.codes.lg.home_theater import LGHomeTheaterCode
from infrared_protocols.commands.samsung import Samsung32Command


@pytest.mark.parametrize(
    ("code", "command"),
    [
        pytest.param(LGHomeTheaterCode.POWER, 0x1E, id="power"),
        pytest.param(LGHomeTheaterCode.VOLUME_UP, 0x17, id="volume_up"),
        pytest.param(LGHomeTheaterCode.NUM_0, 0x4B, id="num_0"),
    ],
)
def test_lg_home_theater_code_builds_samsung32_command(
    code: LGHomeTheaterCode, command: int
) -> None:
    """Codes are sent as Samsung32 frames with the LG home theater address."""
    built = code.to_command()
    assert isinstance(built, Samsung32Command)
    assert built.address == 0x2C
    assert built.command == command
    assert built.repeat_count == 0


def test_lg_home_theater_power_matches_captured_frame() -> None:
    """The power frame is the Samsung32 encoding of the captured 2C 2C 1E E1."""
    timings = LGHomeTheaterCode.POWER.to_command().get_raw_timings()
    data = 0xE11E2C2C
    expected = [4500, -4500]
    for index in range(32):
        expected += [560, -1690 if data >> index & 1 else -560]
    expected.append(560)
    assert timings == expected


def test_lg_home_theater_code_passes_through_repeat_count() -> None:
    """Repeat count must reach the built command."""
    built = LGHomeTheaterCode.VOLUME_UP.to_command(2)
    assert isinstance(built, Samsung32Command)
    assert built.repeat_count == 2

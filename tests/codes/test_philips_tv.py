"""Tests for the Philips TV command codes."""

import pytest

from infrared_protocols.codes.philips.tv import PhilipsTVCode
from infrared_protocols.commands.rc6 import RC6Command


def test_philips_tv_codes_are_unique() -> None:
    """Every code must be distinct.

    ``IntEnum`` silently aliases duplicate values, so a transcription slip
    would otherwise turn two buttons into one without failing anything.
    """
    assert len(PhilipsTVCode) == len(set(PhilipsTVCode))


@pytest.mark.parametrize(
    ("code", "expected_command"),
    [
        pytest.param(PhilipsTVCode.PLAY, 0x2C, id="play"),
        pytest.param(PhilipsTVCode.STOP, 0x31, id="stop"),
        pytest.param(PhilipsTVCode.RECORD, 0x37, id="record"),
        pytest.param(PhilipsTVCode.INFO, 0x0F, id="info"),
    ],
)
def test_philips_tv_code_matches_captured_remote(
    code: PhilipsTVCode, expected_command: int
) -> None:
    """Codes cross-checked against a captured Philips remote must round-trip.

    These four are the buttons whose raw captures were used to verify the
    RC-6 encoder itself.
    """
    command = code.to_command(toggle=1)
    assert isinstance(command, RC6Command)
    assert command.address == 0x00
    assert command.command == expected_command
    assert (
        command.get_raw_timings()
        == RC6Command(
            address=0x00, command=expected_command, toggle=1
        ).get_raw_timings()
    )


def test_philips_tv_code_to_command_defaults() -> None:
    """A code with no arguments must build a single unrepeated RC-6 frame."""
    command = PhilipsTVCode.POWER.to_command()
    assert isinstance(command, RC6Command)
    assert command.address == 0x00
    assert command.command == 0x0C
    assert command.toggle == 0
    assert command.repeat_count == 0
    assert command.modulation == 36000


def test_philips_tv_code_to_command_passes_through_toggle_and_repeats() -> None:
    """Toggle and repeat count must reach the encoded frame."""
    command = PhilipsTVCode.VOLUME_UP.to_command(2, toggle=1)
    assert isinstance(command, RC6Command)
    assert command.toggle == 1
    assert command.repeat_count == 2
    # Three frames in total: the initial one plus two repeats.
    assert command.get_raw_timings().count(2664) == 3

"""Tests for Marantz audio command codes."""

import pytest

from infrared_protocols.codes.marantz.audio import MarantzAudioCode
from infrared_protocols.codes.marantz.models import PM8006
from infrared_protocols.commands.marantz_extended import MarantzExtendedCommand


@pytest.mark.parametrize(
    ("code", "command", "extension"),
    [
        pytest.param(MarantzAudioCode.SOURCE_DVD_PM8006, 0, 10, id="dvd"),
        pytest.param(MarantzAudioCode.SOURCE_AUX_PM8006, 0, 6, id="aux"),
        pytest.param(MarantzAudioCode.INPUT_NEXT, 0, 13, id="input_next"),
        pytest.param(MarantzAudioCode.INPUT_PREVIOUS, 0, 14, id="input_previous"),
        pytest.param(MarantzAudioCode.SPEAKER_A_ON, 35, 0, id="speaker_a_on"),
        pytest.param(MarantzAudioCode.SPEAKER_A_OFF, 35, 1, id="speaker_a_off"),
        pytest.param(MarantzAudioCode.SPEAKER_B_ON, 39, 0, id="speaker_b_on"),
        pytest.param(MarantzAudioCode.SPEAKER_B_OFF, 39, 1, id="speaker_b_off"),
        pytest.param(
            MarantzAudioCode.POWER_AMP_DIRECT_ON, 1, 30, id="power_amp_direct_on"
        ),
        pytest.param(
            MarantzAudioCode.POWER_AMP_DIRECT_OFF, 1, 31, id="power_amp_direct_off"
        ),
    ],
)
def test_pm8006_extended_codes(
    code: MarantzAudioCode, command: int, extension: int
) -> None:
    """Expected decimal values come from the PM8006 service manual, page 25."""
    assert code in PM8006.codes
    built = code.to_command()
    assert isinstance(built, MarantzExtendedCommand)
    assert built.address == 16
    assert built.command == command
    assert built.extension == extension


def test_pm8006_source_mappings() -> None:
    """PM8006 uses its own AUX and DVD codes."""
    assert MarantzAudioCode.SOURCE_DVD not in PM8006.codes
    assert MarantzAudioCode.SOURCE_AUX_1 not in PM8006.codes

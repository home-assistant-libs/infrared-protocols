"""Tests for Marantz audio command codes."""

from infrared_protocols.codes.marantz.audio import MarantzAudioCode
from infrared_protocols.codes.marantz.models import PM8006
from infrared_protocols.commands.marantz_extended import MarantzExtendedCommand


def test_pm8006_dvd_code() -> None:
    """PM8006 service manual page 25 specifies decimal system 16 and extension 10."""
    assert MarantzAudioCode.SOURCE_DVD_PM8006 in PM8006.codes
    assert MarantzAudioCode.SOURCE_DVD not in PM8006.codes
    command = MarantzAudioCode.SOURCE_DVD_PM8006.to_command()
    assert isinstance(command, MarantzExtendedCommand)
    assert command.address == 16
    assert command.command == 0
    assert command.extension == 10

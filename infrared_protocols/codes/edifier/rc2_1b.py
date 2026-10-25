"""Command codes for the Edifier RC2.1B remote."""

from enum import IntEnum

from ...commands import Command
from ...commands.nec import NECCommand


class EdifierRC21BCode(IntEnum):
    """Edifier RC2.1B remote IR command codes."""

    POWER = 0x46
    MUTE = 0x41
    VOLUME_UP_LEFT = 0x05
    VOLUME_DOWN_LEFT = 0x47
    VOLUME_UP_RIGHT = 0x06
    VOLUME_DOWN_RIGHT = 0x49
    BALL_L = 0x07
    BALL_R = 0x5C
    TREBLE_PLUS = 0x09
    TREBLE_MINUS = 0x1E
    BASS_PLUS = 0x45
    BASS_MINUS = 0x5E
    SUBWOOFER_PLUS = 0x03
    SUBWOOFER_MINUS = 0x02
    INPUT_CD = 0x58
    INPUT_PC = 0x1A
    INPUT_DIGITAL = 0x1B
    LIGHT = 0x5B
    ESC = 0x01

    def to_command(self, repeat_count: int = 0) -> Command:
        """Build an NECCommand."""
        return NECCommand(address=0x00, command=self.value, repeat_count=repeat_count)

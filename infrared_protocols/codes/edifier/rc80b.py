"""Command codes for the Edifier RC80B remote.

Inputs are selected with toggle buttons (Line 1/2 and Opt/Coax).
"""

from enum import IntEnum, unique

from ...commands import Command
from ...commands.nec import NECCommand


@unique
class EdifierRC80BCode(IntEnum):
    """Edifier RC80B remote IR command codes."""

    POWER = 0x46
    VOLUME_UP = 0x06
    VOLUME_DOWN = 0x47
    MUTE = 0x41
    PLAY_PAUSE = 0x5F
    FORWARD = 0x5D
    BACK = 0x44
    FX_ON = 0x1A
    FX_OFF = 0x1B
    LINE_1_2 = 0x15
    OPT_COAX = 0x0D
    BLUETOOTH = 0x5C

    def to_command(self, repeat_count: int = 0) -> Command:
        """Build an NECCommand."""
        return NECCommand(address=0xE710, command=self.value, repeat_count=repeat_count)

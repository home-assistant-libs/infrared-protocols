"""Command codes for the Edifier RC20G remote.

This remote has separate left/right volume controls.
"""

from enum import IntEnum

from ...commands import Command
from ...commands.nec import NECCommand


class EdifierRC20GCode(IntEnum):
    """Edifier RC20G remote IR command codes."""

    POWER = 0x46
    MUTE = 0x41
    VOLUME_UP_LEFT = 0x05
    VOLUME_DOWN_LEFT = 0x47
    VOLUME_UP_RIGHT = 0x06
    VOLUME_DOWN_RIGHT = 0x49
    PC = 0x07
    AUX = 0x09
    OPTICAL = 0x45
    COAX = 0x03
    BLUETOOTH = 0x5C
    PREVIOUS = 0x1E
    PLAY_PAUSE = 0x5E
    FORWARD = 0x02

    def to_command(self, repeat_count: int = 0) -> Command:
        """Build an NECCommand."""
        return NECCommand(address=0xE710, command=self.value, repeat_count=repeat_count)

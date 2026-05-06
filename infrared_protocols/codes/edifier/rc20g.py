"""Command codes for the Edifier RC20G remote.

This remote has separate left/right volume controls.
"""

from enum import IntEnum

from ...commands import Command
from ...commands.nec import NECCommand


class EdifierRC20GCode(IntEnum):
    """Edifier RC20G remote IR command codes."""

    POWER = 0xB946
    MUTE = 0xBE41
    VOLUME_UP_LEFT = 0xFA05
    VOLUME_DOWN_LEFT = 0xB847
    VOLUME_UP_RIGHT = 0xF906
    VOLUME_DOWN_RIGHT = 0xB649
    PC = 0xF807
    AUX = 0xF609
    OPTICAL = 0xBA45
    COAX = 0xFC03
    BLUETOOTH = 0xA35C
    PREVIOUS = 0xE11E
    PLAY_PAUSE = 0xA15E
    FORWARD = 0xFD02

    def to_command(self, repeat_count: int = 0) -> Command:
        """Build an NECCommand."""
        return NECCommand(address=0xE710, command=self.value, repeat_count=repeat_count)

"""Command codes for Edifier R1380DB speakers.

Command set used by R1380DB (remote model RC13D).
"""

from enum import IntEnum

from ...commands import Command
from ...commands.nec import NECCommand


class EdifierR1380DBCode(IntEnum):
    """Edifier R1380DB speaker IR command codes."""

    POWER = 0xB946
    VOLUME_UP = 0xF906
    VOLUME_DOWN = 0xB847
    MUTE = 0xBE41
    PLAY_PAUSE = 0xA05F
    FORWARD = 0xA25D
    BACK = 0xBB44
    LINE_1 = 0xE51A
    LINE_2 = 0xE41B
    COAX = 0xF20D
    OPTICAL = 0xEA15
    BLUETOOTH = 0xA35C

    def to_command(self, repeat_count: int = 0) -> Command:
        """Build an NECCommand."""
        return NECCommand(address=0xE710, command=self.value, repeat_count=repeat_count)

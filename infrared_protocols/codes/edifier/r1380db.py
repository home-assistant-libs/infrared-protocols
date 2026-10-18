"""Command codes for Edifier R1380DB speakers.

Command set used by R1380DB (remote model RC13D).
"""

from enum import IntEnum

from ...commands import Command
from ...commands.nec import NECCommand


class EdifierR1380DBCode(IntEnum):
    """Edifier R1380DB speaker IR command codes."""

    POWER = 0x46
    VOLUME_UP = 0x06
    VOLUME_DOWN = 0x47
    MUTE = 0x41
    PLAY_PAUSE = 0x5F
    FORWARD = 0x5D
    BACK = 0x44
    LINE_1 = 0x1A
    LINE_2 = 0x1B
    COAX = 0x0D
    OPTICAL = 0x15
    BLUETOOTH = 0x5C

    def to_command(self, repeat_count: int = 0) -> Command:
        """Build an NECCommand."""
        return NECCommand(address=0xE710, command=self.value, repeat_count=repeat_count)

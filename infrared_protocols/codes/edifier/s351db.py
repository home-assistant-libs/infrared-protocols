"""Command codes for Edifier S351DB speakers (RCA10C remote).

The remote's OPT button has not been captured yet.
"""

from enum import IntEnum, unique

from ...commands import Command
from ...commands.nec import NECCommand


@unique
class EdifierS351DBCode(IntEnum):
    """Edifier S351DB speaker IR command codes."""

    POWER = 0x43
    VOLUME_UP = 0x4C
    VOLUME_DOWN = 0x17
    MUTE = 0x40
    PLAY_PAUSE = 0x50
    NEXT = 0x13
    PREVIOUS = 0x54
    BLUETOOTH = 0x16
    COAX = 0x0C
    PC = 0x51
    AUX = 0x12

    def to_command(self, repeat_count: int = 0) -> Command:
        """Build an NECCommand."""
        return NECCommand(address=0xE710, command=self.value, repeat_count=repeat_count)

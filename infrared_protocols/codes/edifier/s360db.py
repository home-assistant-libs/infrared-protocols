"""Command codes for Edifier S360DB speakers.

Shared command set used by S360DB and RC31A.
"""

from enum import IntEnum

from ...commands import Command
from ...commands.nec import NECCommand


class EdifierS360DBCode(IntEnum):
    """Edifier S360DB speaker IR command codes."""

    POWER = 0x1C
    VOLUME_UP = 0x0C
    VOLUME_DOWN = 0x0F
    PLAY_PAUSE = 0x02
    NEXT = 0x03
    PREVIOUS = 0x40
    BLUETOOTH = 0x0D
    OPTICAL = 0x4C
    COAX = 0x0E
    PC = 0x00
    AUX = 0x01

    def to_command(self, repeat_count: int = 0) -> Command:
        """Build an NECCommand."""
        return NECCommand(address=0x0E78, command=self.value, repeat_count=repeat_count)

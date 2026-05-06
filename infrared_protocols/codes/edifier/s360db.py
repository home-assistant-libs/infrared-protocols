"""Command codes for Edifier S360DB speakers.

Shared command set used by S360DB and RC31A.
"""

from enum import IntEnum

from ...commands import Command
from ...commands.nec import NECCommand


class EdifierS360DBCode(IntEnum):
    """Edifier S360DB speaker IR command codes."""

    POWER = 0xE31C
    VOLUME_UP = 0xF30C
    VOLUME_DOWN = 0xF00F
    PLAY_PAUSE = 0xFD02
    NEXT = 0xFC03
    PREVIOUS = 0xBF40
    BLUETOOTH = 0xF20D
    OPTICAL = 0xB34C
    COAX = 0xF10E
    PC = 0xFF00
    AUX = 0xFE01

    def to_command(self, repeat_count: int = 0) -> Command:
        """Build an NECCommand."""
        return NECCommand(address=0x0E78, command=self.value, repeat_count=repeat_count)

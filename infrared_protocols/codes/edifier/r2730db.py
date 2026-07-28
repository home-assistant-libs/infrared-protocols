"""Command codes for Edifier R2730DB speakers.

Shared command set used by R2730DB and RC10D1.
"""

from enum import IntEnum

from ...commands import Command
from ...commands.nec import NECCommand


class EdifierR2730DBCode(IntEnum):
    """Edifier R2730DB speaker IR command codes."""

    POWER = 0x00
    VOLUME_UP = 0x09
    VOLUME_DOWN = 0x0C
    MUTE = 0x01
    LINE_1 = 0x0A
    LINE_2 = 0x15
    OPTICAL = 0x0D
    COAX = 0x16
    BLUETOOTH = 0x0E

    def to_command(self, repeat_count: int = 0) -> Command:
        """Build an NECCommand."""
        return NECCommand(address=0xE710, command=self.value, repeat_count=repeat_count)

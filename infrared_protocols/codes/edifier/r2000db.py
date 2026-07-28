"""Command codes for Edifier R2000DB speakers."""

from enum import IntEnum

from ...commands import Command
from ...commands.nec import NECCommand


class EdifierR2000DBCode(IntEnum):
    """Edifier R2000DB speaker IR command codes."""

    POWER = 0x00
    VOLUME_UP = 0x09
    VOLUME_DOWN = 0x0C
    MUTE = 0x01
    LINE_1 = 0x0D
    LINE_2 = 0x16
    OPTICAL = 0x0A
    BLUETOOTH = 0x15
    EQ_CLASSIC = 0x0E
    EQ_DYNAMIC = 0x14

    def to_command(self, repeat_count: int = 0) -> Command:
        """Build an NECCommand."""
        return NECCommand(address=0xE710, command=self.value, repeat_count=repeat_count)

"""Command codes for Edifier R1280DB speakers.

Shared command set used by R1280DB, R2730DB, RC10D1, and R2000DB.
"""

from enum import IntEnum

from ...commands import Command
from ...commands.nec import NECCommand


class EdifierR1280DBCode(IntEnum):
    """Edifier R1280DB speaker IR command codes."""

    POWER = 0x01
    VOLUME_UP = 0x09
    VOLUME_DOWN = 0x0C
    MUTE = 0x00
    PLAY_PAUSE = 0x14
    FORWARD = 0x08
    BACK = 0x06
    LINE_1 = 0x0A
    LINE_2 = 0x15
    OPTICAL = 0x0D
    COAX = 0x16
    BLUETOOTH = 0x0E

    def to_command(self, repeat_count: int = 0) -> Command:
        """Build an NECCommand."""
        return NECCommand(address=0xE710, command=self.value, repeat_count=repeat_count)

"""Command codes for Edifier R1280DB speakers.

Shared command set used by R1280DB, R2730DB, RC10D1, and R2000DB.
"""

from enum import IntEnum

from ...commands import Command
from ...commands.nec import NECCommand


class EdifierR1280DBCode(IntEnum):
    """Edifier R1280DB speaker IR command codes."""

    POWER = 0xFE01
    VOLUME_UP = 0xF609
    VOLUME_DOWN = 0xF30C
    MUTE = 0xFF00
    PLAY_PAUSE = 0xEB14
    FORWARD = 0xF708
    BACK = 0xF906
    LINE_1 = 0xF50A
    LINE_2 = 0xEA15
    OPTICAL = 0xF20D
    COAX = 0xE916
    BLUETOOTH = 0xF10E

    def to_command(self, repeat_count: int = 0) -> Command:
        """Build an NECCommand."""
        return NECCommand(address=0xE710, command=self.value, repeat_count=repeat_count)

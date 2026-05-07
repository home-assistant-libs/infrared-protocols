"""Command codes for Edifier R1700BT speakers.

Shared command set used by R1700BT, R1700BTs, RC17A, RC80B, and R1855DB.
"""

from enum import IntEnum

from ...commands import Command
from ...commands.nec import NECCommand


class EdifierR1700BTCode(IntEnum):
    """Edifier R1700BT speaker IR command codes."""

    POWER = 0x46
    VOLUME_UP = 0x06
    VOLUME_DOWN = 0x47
    MUTE = 0x41
    PLAY_PAUSE = 0x5F
    FORWARD = 0x5D
    BACK = 0x44
    FX_ON = 0x1A
    FX_OFF = 0x1B
    LINE_1 = 0x0D
    LINE_2 = 0x15
    BLUETOOTH = 0x5C

    def to_command(self, repeat_count: int = 0) -> Command:
        """Build an NECCommand."""
        return NECCommand(address=0xE710, command=self.value, repeat_count=repeat_count)

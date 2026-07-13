"""Command codes for the Edifier S3000 Pro remote (model RCA10B).

The Line/Bal and Opt/Coax buttons each toggle between their two inputs.
"""

from enum import IntEnum

from ...commands import Command
from ...commands.nec import NECCommand


class EdifierS3000ProCode(IntEnum):
    """Edifier S3000 Pro remote IR command codes."""

    POWER = 0x43
    VOLUME_UP = 0x4C
    VOLUME_DOWN = 0x17
    MUTE = 0x40
    PLAY_PAUSE = 0x50
    NEXT = 0x13
    PREVIOUS = 0x54
    LINE_BAL = 0x51
    OPT_COAX = 0x12
    USB = 0x8D
    BLUETOOTH = 0x0C
    EQ_MONITOR = 0x16
    EQ_DYNAMIC = 0x55
    EQ_CLASSIC = 0x0E
    EQ_VOCAL = 0x4D

    def to_command(self, repeat_count: int = 0) -> Command:
        """Build an NECCommand."""
        return NECCommand(address=0xE710, command=self.value, repeat_count=repeat_count)

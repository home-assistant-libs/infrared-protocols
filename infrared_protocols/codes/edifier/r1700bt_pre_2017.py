"""Command codes for Edifier R1700BT (pre-2017) speakers.

The Pre-2017 revision of the R1700BT uses the RC10B remote (5 buttons, no power button).
"""

from enum import IntEnum

from ...commands import Command
from ...commands.nec import NECCommand


class EdifierR1700BTPre2017Code(IntEnum):
    """Edifier R1700BT (pre-2017) speaker IR command codes."""

    VOLUME_UP = 0x2B
    VOLUME_DOWN = 0x3C
    MUTE = 0x1A
    LINE = 0x5E
    BLUETOOTH = 0x4D

    def to_command(self, repeat_count: int = 0) -> Command:
        """Build an NECCommand."""
        return NECCommand(address=0xE710, command=self.value, repeat_count=repeat_count)

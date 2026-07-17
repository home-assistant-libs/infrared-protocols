"""Command codes for Edifier R1700BT (2017) speakers.

The 2017 revision of the R1700BT uses the RC10G remote (6 buttons, including power).
"""

from enum import IntEnum

from ...commands import Command
from ...commands.nec import NECCommand


class EdifierR1700BT2017Code(IntEnum):
    """Edifier R1700BT (2017) speaker IR command codes."""

    POWER = 0x01
    VOLUME_UP = 0x09
    VOLUME_DOWN = 0x0C
    MUTE = 0x00
    BLUETOOTH = 0x0A
    LINE = 0x15

    def to_command(self, repeat_count: int = 0) -> Command:
        """Build an NECCommand."""
        return NECCommand(address=0xE710, command=self.value, repeat_count=repeat_count)

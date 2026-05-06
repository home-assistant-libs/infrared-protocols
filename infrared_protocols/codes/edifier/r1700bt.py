"""Command codes for Edifier R1700BT speakers.

Shared command set used by R1700BT, R1700BTs, RC17A, RC80B, and R1855DB.
"""

from enum import IntEnum

from ...commands import Command
from ...commands.nec import NECCommand


class EdifierR1700BTCode(IntEnum):
    """Edifier R1700BT speaker IR command codes."""

    POWER = 0xB946
    VOLUME_UP = 0xF906
    VOLUME_DOWN = 0xB847
    MUTE = 0xBE41
    PLAY_PAUSE = 0xA05F
    FORWARD = 0xA25D
    BACK = 0xBB44
    FX_ON = 0xE51A
    FX_OFF = 0xE41B
    LINE_1 = 0xF20D
    LINE_2 = 0xEA15
    BLUETOOTH = 0xA35C

    def to_command(self, repeat_count: int = 0) -> Command:
        """Build an NECCommand."""
        return NECCommand(address=0xE710, command=self.value, repeat_count=repeat_count)

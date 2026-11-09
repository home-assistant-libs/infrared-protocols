"""Command codes for Edifier R2600 speakers (RC31A remote).

Edifier lists the RC31A remote for R2600 units without A.P.F.S.
"""

from enum import IntEnum, unique

from ...commands import Command
from ...commands.nec import NECCommand


@unique
class EdifierR2600Code(IntEnum):
    """Edifier R2600 speaker IR command codes."""

    VOLUME_UP = 0x01
    VOLUME_DOWN = 0x02
    MUTE = 0x09
    PC = 0x00
    AUX = 0x03

    def to_command(self, repeat_count: int = 0) -> Command:
        """Build an NECCommand."""
        return NECCommand(address=0x0E78, command=self.value, repeat_count=repeat_count)

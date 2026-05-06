"""Command codes for the Edifier R1280T speaker."""

from enum import IntEnum

from ...commands import Command
from ...commands.nec import NECCommand


class EdifierR1280TCode(IntEnum):
    """Edifier R1280T speaker IR command codes."""

    VOLUME_UP = 0xC33C
    VOLUME_DOWN = 0xB24D
    MUTE = 0xD42B

    def to_command(self, repeat_count: int = 0) -> Command:
        """Build an NECCommand."""
        return NECCommand(address=0xE710, command=self.value, repeat_count=repeat_count)

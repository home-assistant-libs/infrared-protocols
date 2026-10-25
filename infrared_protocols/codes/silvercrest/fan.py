"""Command codes for SilverCrest fans."""

from enum import IntEnum

from ...commands import Command
from ...commands.symphony import SymphonyCommand


class SilverCrestFanCode(IntEnum):
    """Command codes for SilverCrest fans."""

    POWER = 0x581
    SPEED = 0x582
    MODE = 0x584
    TIMER = 0x588
    OSC = 0x590

    def to_command(self) -> Command:
        """Build Symphony command."""
        return SymphonyCommand.from_code(self.value)

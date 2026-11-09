"""Midea climate button commands."""

from enum import IntEnum, unique

from ...commands import Command
from ...commands.midea import MideaCommand


@unique
class MideaSpecialCode(IntEnum):
    """Dedicated commands; toggle actions require caller-maintained state."""

    SWING_STEP = 0x1
    SWING_TOGGLE = 0x2
    TURBO_TOGGLE = 0x9

    def to_command(self) -> Command:
        """Build the infrared command."""
        return MideaCommand(data=bytes([0xA2, self.value, 255, 255, 255]))

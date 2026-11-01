"""Midea climate button commands."""

from enum import Enum

from ...commands.midea import MideaCommand


class MideaSpecialCode(Enum):
    """Dedicated commands; toggle actions require caller-maintained state."""

    SWING_STEP = 0x1
    SWING_TOGGLE = 0x2
    TURBO_TOGGLE = 0x9

    def to_command(self) -> MideaCommand:
        """Build the infrared command."""
        return MideaCommand(data=bytes([0xA2, self.value, 255, 255, 255]))

"""Command codes for SilverCrest fans."""

from enum import IntEnum

from ...commands import Command
from ...commands.symphony import SymphonyCommand, SymphonyKey


class SilverCrestFanCode(IntEnum):
    """Command codes for SilverCrest fans."""

    POWER = SymphonyKey.K1
    SPEED = SymphonyKey.K2
    MODE = SymphonyKey.K3
    TIMER = SymphonyKey.K4
    OSC = SymphonyKey.K5

    def to_command(self) -> Command:
        """Build Symphony command."""
        return SymphonyCommand(
            custom_code=3,
            control_word=self.value,
            frame_head=2,
        )

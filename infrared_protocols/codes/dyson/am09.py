"""Dyson AM09 (Hot+Cool) command codes."""

from enum import IntEnum

from ...commands import Command
from ...commands.dyson import DysonAm09Command


class DysonAm09Code(IntEnum):
    """Dyson AM09 IR command codes."""

    # The AM09 remote has a single standby button, not discrete on/off codes.
    POWER = 0x01
    COOL_ON = 0xA8
    SWING = 0x30
    SPEED_UP = 0x55
    SPEED_DOWN = 0xFE
    TIMER = 0x87
    HEAT_UP = 0x7B
    HEAT_DOWN = 0xCC
    VENT_THIN = 0x4A
    VENT_WIDE = 0xB7

    def to_command(self) -> Command:
        """Build a Dyson AM09 command for this code."""
        return DysonAm09Command(code=self.value)

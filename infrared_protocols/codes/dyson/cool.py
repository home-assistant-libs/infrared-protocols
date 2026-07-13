"""Dyson cool mode command codes.

Codes are 15-bit values: 7-bit preamble (0b1001000) + 8-bit command byte,
reverse-engineered from real Broadlink learn_command captures.
"""

from enum import IntEnum

from ...commands import Command
from ...commands.dyson import DysonCoolCommand


class DysonCoolCode(IntEnum):
    """Dyson Cool mode IR command codes."""

    ON = 0x4800
    COOL_ON = 0x4801
    OFF = 0x4802  # cool_off
    SWING = 0x48A9
    SPEED_UP = 0x4854  # temp_up
    SPEED_DOWN = 0x48FD  # temp_down
    TIME_UP = 0x487A
    TIME_DOWN = 0x48CC

    def to_command(self, repeat_count: int = 0) -> Command:
        """Build a Dyson Cool command for this code."""
        return DysonCoolCommand(payload=self.value, repeat_count=repeat_count)

"""Dyson AM09 (Hot+Cool) command codes.

Codes are 15-bit values: 7-bit preamble (0b0011000) + 8-bit command byte.
"""

from enum import IntEnum

from ...commands import Command
from ...commands.dyson import DysonAm09Command


class DysonAm09Code(IntEnum):
    """Dyson AM09 IR command codes."""

    ON = 0x1801
    COOL_ON = 0x18A8
    SWING = 0x1830
    SPEED_UP = 0x1855
    SPEED_DOWN = 0x18FE
    TIMER = 0x1887
    HEAT_UP = 0x187B
    HEAT_DOWN = 0x18CC
    VENT_THIN = 0x184A
    VENT_WIDE = 0x18B7

    def to_command(self) -> Command:
        """Build a Dyson AM09 command for this code."""
        return DysonAm09Command(payload=self.value)

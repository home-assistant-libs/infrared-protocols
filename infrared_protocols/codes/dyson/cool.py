"""Dyson cool mode command codes."""

from enum import IntEnum

from ...commands import Command
from ...commands.dyson import DysonCoolCommand


class DysonCoolCode(IntEnum):
    """Dyson Cool mode IR command codes."""

    ON = 0x00
    COOL_ON = 0x01
    OFF = 0x02
    SWING = 0xA9
    SPEED_UP = 0x54
    SPEED_DOWN = 0xFD
    TIME_UP = 0x7A
    TIME_DOWN = 0xCC

    def to_command(self) -> Command:
        """Build a Dyson Cool command for this code."""
        return DysonCoolCommand(code=self.value)

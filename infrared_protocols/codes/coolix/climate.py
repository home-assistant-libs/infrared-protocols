"""Coolix climate button commands."""

from enum import IntEnum, unique

from ...commands import Command
from ...commands.coolix import CoolixCommand


@unique
class CoolixCode(IntEnum):
    """Dedicated commands; toggle actions require caller-maintained state."""

    POWER_OFF = 0xB27BE0
    SWING_TOGGLE = 0xB26BE0
    LIGHT_TOGGLE = 0xB5F5A5
    SILENCE_FROST_PROTECTION = 0xB5F5B6

    def to_command(self) -> Command:
        """Build the infrared command."""
        return CoolixCommand(first=self.value, second=self.value)

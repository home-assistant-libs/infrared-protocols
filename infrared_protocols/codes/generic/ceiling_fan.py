"""Command codes for generic ceiling fan with light remote control."""

from enum import IntEnum, unique

from ...commands import Command
from ...commands.nec import NECCommand


@unique
class GenericCeilingFanCode(IntEnum):
    """Generic ceiling fan with light remote control IR command codes.

    The remote sends NEC frames using address byte 0x01, which is the standard
    NEC address 0x01 plus its inversion 0xFE. Fan and light are each toggled by
    a single key, so there are no separate on and off codes.
    """

    FAN_TOGGLE = 0x09
    FAN_LOW = 0x03
    FAN_MEDIUM = 0x07
    FAN_HIGH = 0x0B

    LIGHT_TOGGLE = 0x01
    LIGHT_BRIGHTNESS_UP = 0x0A
    LIGHT_BRIGHTNESS_DOWN = 0x02
    LIGHT_COLOR_WARMER = 0x05
    LIGHT_COLOR_COOLER = 0x04

    def to_command(self, repeat_count: int = 0) -> Command:
        """Build a NEC command."""
        return NECCommand(
            address=0xFE01,
            command=self.value,
            repeat_count=repeat_count,
        )

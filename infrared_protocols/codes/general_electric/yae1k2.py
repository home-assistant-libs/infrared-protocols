"""Command codes for the GE YAE1K2 AC remote."""

from enum import IntEnum

from ...commands import Command
from ...commands.general_electric import GEACCommand

YAE1K2_ADDRESS = 0xEB


class YAE1K2Code(IntEnum):
    """GE YAE1K2 AC remote IR command codes."""

    COOL_MODE = 0x00
    TEMP_UP = 0x20
    HIGH = 0x40
    MED = 0x50
    FAN_MODE = 0x80
    LOW = 0x90
    TEMP_DOWN = 0xA0
    POWER = 0xD0

    def to_command(self) -> Command:
        """Build a GEACCommand for this GE YAE1K2 code."""
        return GEACCommand(address=YAE1K2_ADDRESS, command=self.value)

"""Hob2Hood extractor fan and light commands."""

from enum import Enum

from ...commands.hob2hood import Hob2HoodCommand


class Hob2HoodCode(Enum):
    """Commands shared by compatible Hob2Hood extractors."""

    LIGHT_OFF = 0xD5
    LIGHT_ON = 0xD2
    FAN_OFF = 0xD8
    FAN_LOW = 0x6C
    FAN_MEDIUM = 0x6F
    FAN_HIGH = 0xE1
    FAN_MAX = 0x72

    def to_command(self) -> Hob2HoodCommand:
        """Build the infrared command."""
        return Hob2HoodCommand(command=self.value)

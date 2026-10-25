"""Command codes for generic 21-key LED remote control."""

from ....commands import Command
from ....commands.nec import NECCommand
from .base import BaseGenericLEDCode


class Generic21KeyCode(BaseGenericLEDCode):
    """Generic 21-key LED remote control IR command codes."""

    ON = 0x45
    AUTO = 0x46
    OFF = 0x47
    SPEED_UP = 0x44
    SPEED_DOWN = 0x07
    MODE_UP = 0x40
    MODE_DOWN = 0x15
    BRIGHTNESS_UP = 0x43
    BRIGHTNESS_DOWN = 0x09
    RED = 0x16
    GREEN = 0x19
    BLUE = 0x0D
    LIGHT_YELLOW = 0x0C
    MOCCASIN = 0x18
    YELLOW = 0x5E
    ORANGE = 0x08
    GHOST_WHITE = 0x1C
    SKY_BLUE = 0x5A
    PINK = 0x42
    LIGHT_GREEN = 0x52
    FLORAL_WHITE = 0x4A

    def to_command(self, repeat_count: int = 0) -> Command:
        """Build a NEC command."""
        return NECCommand(
            address=0xFF00,
            command=self.value,
            repeat_count=repeat_count,
        )

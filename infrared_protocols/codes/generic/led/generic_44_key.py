"""Command codes for generic 44-key LED remote control."""

from enum import IntEnum

from ....commands import Command
from ....commands.nec import NECCommand


class Generic44KeyCode(IntEnum):
    """Generic 44-key LED remote control IR command codes."""

    ON = 0x40
    OFF = 0x41

    BRIGHTNESS_UP = 0x5C
    BRIGHTNESS_DOWN = 0x5D

    RED_UP = 0x14
    GREEN_UP = 0x15
    BLUE_UP = 0x16
    RED_DOWN = 0x10
    GREEN_DOWN = 0x11
    BLUE_DOWN = 0x12

    QUICK = 0x17
    SLOW = 0x13

    DIY1 = 0x0C
    DIY2 = 0x0D
    DIY3 = 0x0E
    DIY4 = 0x08
    DIY5 = 0x09
    DIY6 = 0x0A

    AUTO = 0x0F

    FLASH = 0x0B
    JUMP3 = 0x04
    JUMP7 = 0x05
    FADE3 = 0x06
    FADE7 = 0x07

    RED = 0x58
    GREEN = 0x59
    BLUE = 0x45
    WHITE = 0x44
    TOMATO = 0x54
    LIGHT_GREEN = 0x55
    DEEP_BLUE = 0x49
    FLORAL_WHITE = 0x48
    ORANGE = 0x50
    TURQUOISE = 0x51
    PURPLE = 0x4D
    LAVENDER_BLUSH = 0x4C
    YELLOWISH = 0x1C
    CYAN = 0x1D
    MAGENTA = 0x1E
    GHOST_WHITE = 0x1F
    YELLOW = 0x18
    AQUA = 0x19
    PINK = 0x1A
    LIGHT_CYAN = 0x1B

    def to_command(self, repeat_count: int = 0) -> Command:
        """Build a NEC command."""
        return NECCommand(
            address=0xFF00,
            command=self.value,
            repeat_count=repeat_count,
        )

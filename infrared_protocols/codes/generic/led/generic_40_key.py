"""Command codes for generic 40-key LED remote control."""

from enum import IntEnum

from ....commands import Command
from ....commands.nec import NECCommand


class Generic40KeyCode(IntEnum):
    """Generic 40-key LED remote control IR command codes."""

    ON = 0x40
    OFF = 0x41

    BRIGHTNESS_UP = 0x5C
    BRIGHTNESS_DOWN = 0x5D

    WHITE_BRIGHTNESS_UP = 0x14
    WHITE_BRIGHTNESS_DOWN = 0x15
    WHITE_ON = 0x16
    WHITE_OFF = 0x17
    WHITE_BRIGHTNESS_25 = 0x10
    WHITE_BRIGHTNESS_50 = 0x11
    WHITE_BRIGHTNESS_75 = 0x12
    WHITE_BRIGHTNESS_100 = 0x13

    QUICK = 0x0F
    SLOW = 0x0B

    JUMP3 = 0x0C
    FADE3 = 0x0D
    JUMP7 = 0x0E
    FADE7 = 0x08
    FLASH = 0x09
    AUTO = 0x0A

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

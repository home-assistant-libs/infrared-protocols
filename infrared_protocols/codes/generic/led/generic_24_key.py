"""Command codes for generic 24-key LED remote control."""

from enum import IntEnum

from ....commands import Command
from ....commands.nec import NECCommand


class Generic24KeyCode(IntEnum):
    """Generic 24-key LED remote control IR command codes."""

    ON = 0x03
    OFF = 0x02
    BRIGHTNESS_UP = 0x00
    BRIGHTNESS_DOWN = 0x01
    FLASH = 0x0B
    STROBE = 0x0F
    FADE = 0x13
    SMOOTH = 0x17
    RED = 0x04
    GREEN = 0x05
    BLUE = 0x06
    WHITE = 0x07
    TOMATO = 0x08
    LIGHT_GREEN = 0x09
    SKY_BLUE = 0x0A
    ORANGE_RED = 0x0C
    CYAN = 0x0D
    REBECCA_PURPLE = 0x0E
    ORANGE = 0x10
    TURQUOISE = 0x11
    PURPLE = 0x12
    YELLOW = 0x14
    DARK_CYAN = 0x15
    PLUM = 0x16

    def to_command(self, repeat_count: int = 0) -> Command:
        """Build a NEC command."""
        return NECCommand(
            address=0xEF00,
            command=self.value,
            repeat_count=repeat_count,
        )

"""Command codes for Tween Light LED Strip.

Tween light is a brand marketed by the european home improvement retail chain BAUHAUS.
The LED strip comes with a 24-key remote control, which is also sold with many other
no-name LED controllers.

https://www.bauhaus.info/led-streifen/tween-light-led-band/p/30293612
"""

from enum import IntEnum

from ...commands import Command
from ...commands.nec import NECCommand


class TweenLightLEDStripCode(IntEnum):
    """Tween Light LED Strip IR command codes."""

    ON = 0xFC03
    OFF = 0xFD02
    BRIGHTNESS_UP = 0xFF00
    BRIGHTNESS_DOWN = 0xFE01
    FLASH = 0xF40B
    STROBE = 0xF00F
    FADE = 0xEC13
    SMOOTH = 0xE817
    RED = 0xFB04
    GREEN = 0xFA05
    BLUE = 0xF906
    WHITE = 0xF708
    TOMATO = 0xF708
    LIGHT_GREEN = 0xF609
    SKY_BLUE = 0xF906
    ORANGE_RED = 0xF30C
    CYAN = 0xF20D
    REBECCA_PURPLE = 0xF10E
    ORANGE = 0xEF10
    TURQUOISE = 0xEE11
    PURPLE = 0xED12
    YELLOW = 0xEB14
    DARK_CYAN = 0xEA15
    PLUM = 0xE916

    def to_command(self, repeat_count: int = 0) -> Command:
        """Build a NEC command."""
        return NECCommand(
            address=0xEF00,
            command=self.value,
            repeat_count=repeat_count,
        )

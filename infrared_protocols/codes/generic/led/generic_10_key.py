"""Command codes for generic 10-key LED candle remote control."""

from ....commands import Command
from ....commands.nec import NECCommand
from .base import BaseGenericLEDCode


class Generic10KeyCode(BaseGenericLEDCode):
    """Generic 10-key LED candle remote control IR command codes."""

    ON = 0x01
    OFF = 0x00
    BRIGHTNESS_UP = 0x14
    BRIGHTNESS_DOWN = 0x0E

    TIMER_2H = 0x0C
    TIMER_4H = 0x09
    TIMER_6H = 0x0A
    TIMER_8H = 0x15

    CANDLE = 0x0D
    LIGHT = 0x16

    def to_command(self, repeat_count: int = 0) -> Command:
        """Build a NEC command."""
        return NECCommand(
            address=0xFF00,
            command=self.value,
            repeat_count=repeat_count,
        )

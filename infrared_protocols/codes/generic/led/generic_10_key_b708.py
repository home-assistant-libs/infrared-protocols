"""Command codes for generic 10-key LED candle remote control on NEC address 0xB708."""

from ....commands import Command
from ....commands.nec import NECCommand
from .base import BaseGenericLEDCode


class Generic10KeyB708Code(BaseGenericLEDCode):
    """Generic 10-key LED candle remote control IR command codes.

    Same key layout as Generic10KeyCode but on a different address, used by e.g.
    Flinq and Vinkor candles.
    """

    ON = 0x00
    OFF = 0x02
    BRIGHTNESS_UP = 0x12
    BRIGHTNESS_DOWN = 0x10

    TIMER_2H = 0x04
    TIMER_4H = 0x06
    TIMER_6H = 0x08
    TIMER_8H = 0x0A

    CANDLE = 0x0C
    LIGHT = 0x0E

    def to_command(self, repeat_count: int = 0) -> Command:
        """Build a NEC command."""
        return NECCommand(
            address=0xB708,
            command=self.value,
            repeat_count=repeat_count,
        )

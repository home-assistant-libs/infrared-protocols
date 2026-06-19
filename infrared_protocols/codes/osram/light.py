"""Command codes for OSRAM LEDVANCE RGB light bulbs."""

from enum import IntEnum

from ...commands import Command
from ...commands.nec import NECCommand

OSRAM_ADDRESS = 0xFF00


class OsramLightCode(IntEnum):
    """OSRAM LEDVANCE RGB light bulb IR command codes."""

    BRIGHTNESS_UP = 0x00
    BRIGHTNESS_DOWN = 0x02
    WHITE = 0x03
    OFF = 0x06
    ON = 0x07

    # Colors named by their approximate hue in degrees
    HUE_000 = 0x08
    HUE_015 = 0x0C
    HUE_030 = 0x10
    HUE_045 = 0x14
    HUE_060 = 0x18

    HUE_120 = 0x09
    HUE_135 = 0x0D
    HUE_150 = 0x11
    HUE_165 = 0x15
    HUE_180 = 0x19

    HUE_240 = 0x0A
    HUE_255 = 0x0E
    HUE_270 = 0x12
    HUE_285 = 0x16
    HUE_300 = 0x1A

    FLASH = 0x0F
    STROBE = 0x13
    SMOOTH = 0x17
    MODE = 0x1B

    def to_command(self, repeat_count: int = 0) -> Command:
        """Build a NECCommand for a light code."""
        return NECCommand(
            address=OSRAM_ADDRESS,
            command=self.value,
            repeat_count=repeat_count,
        )

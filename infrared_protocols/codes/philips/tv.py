"""Command codes for Philips TVs."""

from enum import IntEnum

from ...commands import Command
from ...commands.rc6 import RC6Command

PHILIPS_TV_ADDRESS = 0x00


class PhilipsTVCode(IntEnum):
    """Philips TV IR command codes."""

    POWER = 0x0C
    MUTE = 0x0D
    VOLUME_UP = 0x10
    VOLUME_DOWN = 0x11

    NUM_0 = 0x00
    NUM_1 = 0x01
    NUM_2 = 0x02
    NUM_3 = 0x03
    NUM_4 = 0x04
    NUM_5 = 0x05
    NUM_6 = 0x06
    NUM_7 = 0x07
    NUM_8 = 0x08
    NUM_9 = 0x09

    CHANNEL_UP = 0x20
    CHANNEL_DOWN = 0x21

    NAV_UP = 0x58
    NAV_DOWN = 0x59
    NAV_LEFT = 0x5A
    NAV_RIGHT = 0x5B
    OK = 0x5C
    BACK = 0x0A
    HOME = 0x54
    OPTIONS = 0x40

    PLAY = 0x2C
    PAUSE = 0x30
    STOP = 0x31
    RECORD = 0x37
    REWIND = 0x2B
    FAST_FORWARD = 0x28

    SOURCE = 0x38
    INFO = 0x0F
    GUIDE = 0xCC
    TEXT = 0x3C
    SUBTITLE = 0x4B
    FORMAT = 0xF5
    SETTINGS = 0xBF
    AMBILIGHT = 0x8F

    RED = 0x6D
    GREEN = 0x6E
    YELLOW = 0x6F
    BLUE = 0x70

    NETFLIX = 0x76
    YOUTUBE = 0x79
    PRIME_VIDEO = 0xBA

    def to_command(self, repeat_count: int = 0, *, toggle: int = 0) -> Command:
        """Build an RC-6 command for this Philips TV code.

        Flip ``toggle`` between successive presses of the same key, otherwise
        the TV reads the second press as a repeat of the first and ignores it.
        """
        return RC6Command(
            address=PHILIPS_TV_ADDRESS,
            command=self.value,
            toggle=toggle,
            repeat_count=repeat_count,
        )

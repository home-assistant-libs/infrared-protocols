"""Command codes for Sony televisions.

Sony televisions use 12-bit SIRC on address 1, a command set that has stayed
stable across Bravia generations and their predecessors. Address 1 is not
exclusive to televisions: Sony remotes for other device types carry these keys
too, and third-party sets have cloned them.

Codes are unioned across 50 remotes driving this command set. Every entry is
one that at least three of them agree on, but not every television responds to
every code. Older sets in particular use ENTER rather than OK to confirm a
selection.
"""

from enum import IntEnum

from ...commands import Command
from ...commands.sony import SonyCommand

SONY_TV_ADDRESS = 0x01
SONY_TV_ADDRESS_BITS = 5


class SonyTVCode(IntEnum):
    """Sony television IR command codes."""

    POWER = 0x15
    MUTE = 0x14
    VOLUME_UP = 0x12
    VOLUME_DOWN = 0x13
    CHANNEL_UP = 0x10
    CHANNEL_DOWN = 0x11
    INPUT = 0x25
    SLEEP = 0x36

    NUM_0 = 0x09
    NUM_1 = 0x00
    NUM_2 = 0x01
    NUM_3 = 0x02
    NUM_4 = 0x03
    NUM_5 = 0x04
    NUM_6 = 0x05
    NUM_7 = 0x06
    NUM_8 = 0x07
    NUM_9 = 0x08
    # Separates major and minor channel numbers, as in 5-1.
    CHANNEL_DASH = 0x20
    ENTER = 0x0B

    NAV_UP = 0x74
    NAV_DOWN = 0x75
    NAV_LEFT = 0x34
    NAV_RIGHT = 0x33
    OK = 0x65
    HOME = 0x60
    EXIT = 0x16

    INFO = 0x3A
    JUMP = 0x3B
    FAVORITES = 0x18
    CLOSED_CAPTIONS = 0x23
    AUDIO = 0x17
    PICTURE = 0x64
    TV = 0x24
    HDMI = 0x39
    COMPONENT = 0x45

    RED = 0x7A
    GREEN = 0x7B
    YELLOW = 0x7C
    BLUE = 0x7D

    def to_command(self) -> Command:
        """Build a SONY SIRC command for this Sony television code."""
        return SonyCommand(
            address=SONY_TV_ADDRESS,
            address_bits=SONY_TV_ADDRESS_BITS,
            command=self.value,
        )

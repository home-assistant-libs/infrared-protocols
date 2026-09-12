"""IR command codes for Anthem MRX/AVM receivers and pre-amplifiers.

Codes are identical across the Anthem MRX/AVM lineup (MRX 310/510/710,
MRX 520/720/1120, MRX x40, AVM 60, AVM 70/90) -- verified by decoding the
manufacturer's published IR hex/Pronto tables for both the MRX x10/x20/AVM 60
generation and the newer 4K/8K (MRX x40, AVM 70/90) generation and confirming
they encode to the same NEC address/command pairs.

This was verified with Anthem Technical Support.
"""

from enum import Enum

from ...commands import Command
from ...commands.nec import NECCommand

_ADDR_MAIN = 0x6A85
_ADDR_EXT = 0x9A85


class AnthemCode(Enum):
    """IR command code for an Anthem MRX/AVM receiver or pre-amplifier.

    The tuple value is ``(address, command)`` for the extended NEC protocol.
    """

    # Main Zone
    POWER = (_ADDR_MAIN, 0x97)
    STANDBY = (_ADDR_MAIN, 0x93)
    BASS = (_ADDR_MAIN, 0x6F)
    DIM = (_ADDR_MAIN, 0xF3)
    BALANCE = (_ADDR_EXT, 0x72)
    TREBLE = (_ADDR_MAIN, 0x70)
    LEVEL = (_ADDR_MAIN, 0x39)
    NUM_1 = (_ADDR_MAIN, 0x80)
    NUM_2 = (_ADDR_MAIN, 0x81)
    NUM_3 = (_ADDR_MAIN, 0x82)
    NUM_4 = (_ADDR_MAIN, 0x83)
    NUM_5 = (_ADDR_MAIN, 0x84)
    NUM_6 = (_ADDR_MAIN, 0x85)
    NUM_7 = (_ADDR_MAIN, 0x86)
    NUM_8 = (_ADDR_MAIN, 0x87)
    NUM_9 = (_ADDR_MAIN, 0x88)
    NUM_0 = (_ADDR_MAIN, 0x89)
    PRESET = (_ADDR_MAIN, 0x6E)
    INPUT_CYCLE = (_ADDR_MAIN, 0x9B)
    SETUP_MENU = (_ADDR_MAIN, 0x3E)
    INFO = (_ADDR_MAIN, 0x37)
    CURSOR_LEFT = (_ADDR_MAIN, 0x60)
    CURSOR_UP = (_ADDR_MAIN, 0x5D)
    SELECT = (_ADDR_MAIN, 0x96)
    CURSOR_RIGHT = (_ADDR_MAIN, 0x5F)
    CURSOR_DOWN = (_ADDR_MAIN, 0x5E)
    CLEAR = (_ADDR_EXT, 0x96)
    DYNAMICS = (_ADDR_MAIN, 0x3D)
    MODE = (_ADDR_MAIN, 0x2D)
    LAST = (_ADDR_EXT, 0x94)
    VOLUME_UP = (_ADDR_MAIN, 0x9F)
    VOLUME_DOWN = (_ADDR_MAIN, 0x9E)
    MUTE = (_ADDR_MAIN, 0x99)
    LIP_SYNC = (_ADDR_EXT, 0x92)
    PAGE_PRESET_UP = (_ADDR_EXT, 0x9B)
    PAGE_PRESET_DOWN = (_ADDR_EXT, 0x9C)
    INPUT_1 = (_ADDR_MAIN, 0x0F)
    INPUT_2 = (_ADDR_MAIN, 0x8C)
    INPUT_3 = (_ADDR_MAIN, 0x90)
    INPUT_4 = (_ADDR_MAIN, 0x25)
    INPUT_5 = (_ADDR_MAIN, 0x14)
    INPUT_6 = (_ADDR_MAIN, 0x26)
    INPUT_7 = (_ADDR_MAIN, 0x13)
    INPUT_8 = (_ADDR_MAIN, 0x91)
    INPUT_9 = (_ADDR_EXT, 0x90)
    INPUT_10 = (_ADDR_EXT, 0xA0)
    INPUT_11 = (_ADDR_EXT, 0xA1)
    INPUT_12 = (_ADDR_EXT, 0xA2)
    INPUT_13 = (_ADDR_EXT, 0xA3)
    INPUT_14 = (_ADDR_EXT, 0xA4)
    INPUT_15 = (_ADDR_EXT, 0xA5)
    INPUT_16 = (_ADDR_EXT, 0xA6)
    INPUT_17 = (_ADDR_EXT, 0xA7)
    INPUT_18 = (_ADDR_EXT, 0xA8)
    INPUT_19 = (_ADDR_EXT, 0xA9)
    INPUT_20 = (_ADDR_EXT, 0xAA)
    INPUT_21 = (_ADDR_EXT, 0xC6)
    INPUT_22 = (_ADDR_EXT, 0xC7)
    INPUT_23 = (_ADDR_EXT, 0xC8)
    INPUT_24 = (_ADDR_EXT, 0xC9)
    INPUT_25 = (_ADDR_EXT, 0xCA)
    INPUT_26 = (_ADDR_EXT, 0xCB)
    INPUT_27 = (_ADDR_EXT, 0xCC)
    INPUT_28 = (_ADDR_EXT, 0xCD)
    INPUT_29 = (_ADDR_EXT, 0xCE)
    INPUT_30 = (_ADDR_EXT, 0xCF)

    # Zone 2
    ZONE2_POWER = (_ADDR_EXT, 0xD0)
    ZONE2_STANDBY = (_ADDR_EXT, 0xD1)
    ZONE2_VOLUME_UP = (_ADDR_EXT, 0xE7)
    ZONE2_VOLUME_DOWN = (_ADDR_EXT, 0xE8)
    ZONE2_MUTE = (_ADDR_EXT, 0xE9)
    ZONE2_INPUT_CYCLE = (_ADDR_EXT, 0x97)
    ZONE2_PRESET_UP = (_ADDR_EXT, 0xE2)
    ZONE2_PRESET_DOWN = (_ADDR_EXT, 0xE1)
    ZONE2_INPUT_1 = (_ADDR_EXT, 0xD2)
    ZONE2_INPUT_2 = (_ADDR_EXT, 0xD3)
    ZONE2_INPUT_3 = (_ADDR_EXT, 0xD4)
    ZONE2_INPUT_4 = (_ADDR_EXT, 0xD5)
    ZONE2_INPUT_5 = (_ADDR_EXT, 0xD6)
    ZONE2_INPUT_6 = (_ADDR_EXT, 0xD7)
    ZONE2_INPUT_7 = (_ADDR_EXT, 0xD8)
    ZONE2_INPUT_8 = (_ADDR_EXT, 0xD9)
    ZONE2_INPUT_9 = (_ADDR_EXT, 0xDA)
    ZONE2_INPUT_10 = (_ADDR_EXT, 0xB0)
    ZONE2_INPUT_11 = (_ADDR_EXT, 0xB1)
    ZONE2_INPUT_12 = (_ADDR_EXT, 0xB2)
    ZONE2_INPUT_13 = (_ADDR_EXT, 0xB3)
    ZONE2_INPUT_14 = (_ADDR_EXT, 0xB4)
    ZONE2_INPUT_15 = (_ADDR_EXT, 0xB5)
    ZONE2_INPUT_16 = (_ADDR_EXT, 0xB6)
    ZONE2_INPUT_17 = (_ADDR_EXT, 0xB7)
    ZONE2_INPUT_18 = (_ADDR_EXT, 0xB8)
    ZONE2_INPUT_19 = (_ADDR_EXT, 0xB9)
    ZONE2_INPUT_20 = (_ADDR_EXT, 0xBB)
    ZONE2_INPUT_21 = (_ADDR_EXT, 0xBC)
    ZONE2_INPUT_22 = (_ADDR_EXT, 0xBD)
    ZONE2_INPUT_23 = (_ADDR_EXT, 0xBE)
    ZONE2_INPUT_24 = (_ADDR_EXT, 0xBF)
    ZONE2_INPUT_25 = (_ADDR_EXT, 0xC0)
    ZONE2_INPUT_26 = (_ADDR_EXT, 0xC1)
    ZONE2_INPUT_27 = (_ADDR_EXT, 0xC2)
    ZONE2_INPUT_28 = (_ADDR_EXT, 0xC3)
    ZONE2_INPUT_29 = (_ADDR_EXT, 0xC4)
    ZONE2_INPUT_30 = (_ADDR_EXT, 0xC5)

    def to_command(self, repeat_count: int = 0) -> Command:
        """Build the IR command for this code."""
        address, command = self.value
        return NECCommand(
            address=address,
            command=command,
            repeat_count=repeat_count,
        )

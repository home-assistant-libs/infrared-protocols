"""Command codes for LG TVs."""

from enum import IntEnum

from ...commands import Command, NECCommand


class LGTVCode(IntEnum):
    """LG TV IR command codes."""

    BACK = 0x28
    CHANNEL_DOWN = 0x01
    CHANNEL_UP = 0x00
    EXIT = 0x5B
    FAST_FORWARD = 0x8E
    GUIDE = 0xA9
    HDMI_1 = 0xCE
    HDMI_2 = 0xCC
    HDMI_3 = 0xE9
    HDMI_4 = 0xDA
    HOME = 0x7C
    INFO = 0xAA
    INPUT = 0x0B
    MENU = 0x43
    MUTE = 0x09
    NAV_DOWN = 0x41
    NAV_LEFT = 0x07
    NAV_RIGHT = 0x06
    NAV_UP = 0x40
    NUM_0 = 0x10
    NUM_1 = 0x11
    NUM_2 = 0x12
    NUM_3 = 0x13
    NUM_4 = 0x14
    NUM_5 = 0x15
    NUM_6 = 0x16
    NUM_7 = 0x17
    NUM_8 = 0x18
    NUM_9 = 0x19
    OK = 0x44
    PAUSE = 0xBA
    PLAY = 0xB0
    POWER = 0x08
    POWER_ON = 0xC4
    POWER_OFF = 0xC5
    REWIND = 0x8F
    STOP = 0xB1
    VOLUME_DOWN = 0x03
    VOLUME_UP = 0x02


def make_command(code: LGTVCode, repeat_count: int = 0) -> Command:
    """Get the NECCommand for an LG TV IR code."""
    return NECCommand(
        address=0xFB04, command=code, modulation=38000, repeat_count=repeat_count
    )

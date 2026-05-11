"""Command codes for Samsung TVs (Samsung32 protocol)."""

from enum import IntEnum

from ...commands import Command
from ...commands.samsung import Samsung32Command


class SamsungTVCode(IntEnum):
    """Samsung TV IR command codes."""

    POWER = 0x02
    POWER_OFF = 0x98
    POWER_ON = 0x99
    SOURCE = 0x01
    SETTINGS = 0x1A
    INFO = 0x1F
    EXIT = 0x2D
    RETURN = 0x58
    HOME = 0x79
    RED = 0x6C
    GREEN = 0x14
    YELLOW = 0x15
    BLUE = 0x16
    NAV_UP = 0x60
    NAV_DOWN = 0x61
    NAV_LEFT = 0x65
    NAV_RIGHT = 0x62
    OK = 0x68
    MUTE = 0x0F
    VOLUME_UP = 0x07
    VOLUME_DOWN = 0x0B
    CHANNEL_UP = 0x12
    CHANNEL_DOWN = 0x10
    PREVIOUS_CHANNEL = 0x13
    HDMI_1 = 0xE9
    HDMI_2 = 0xBE
    HDMI_3 = 0xC2
    HDMI_4 = 0xC5
    NUM_0 = 0x11
    NUM_1 = 0x04
    NUM_2 = 0x05
    NUM_3 = 0x06
    NUM_4 = 0x08
    NUM_5 = 0x09
    NUM_6 = 0x0A
    NUM_7 = 0x0C
    NUM_8 = 0x0D
    NUM_9 = 0x0E
    PLAY = 0x47
    PAUSE = 0x4A
    STOP = 0x46
    FAST_FORWARD = 0x48
    REWIND = 0x45
    RECORD = 0x49
    TOOLS = 0x4B
    BROWSER = 0x37
    TV = 0x1B
    AD_SUBTITLE = 0x25
    E_MANUAL = 0x3F

    def to_command(self, repeat_count: int = 0) -> Command:
        """Build a Samsung32 command for this Samsung TV code."""
        return Samsung32Command(
            address=0x07,
            command=self.value,
            repeat_count=repeat_count,
        )

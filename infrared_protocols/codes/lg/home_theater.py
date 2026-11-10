"""Command codes for LG Blu-ray home theaters (Samsung32 protocol).

Captured from the AKB73775801 remote that ships with the BH4030S.
"""

from enum import IntEnum, unique

from ...commands import Command
from ...commands.samsung import Samsung32Command

LG_HOME_THEATER_ADDRESS = 0x2C


@unique
class LGHomeTheaterCode(IntEnum):
    """LG home theater IR command codes."""

    ASTERISK = 0x30
    AUDIO = 0x36
    BACK = 0xA2
    BLUE = 0x6F
    CLEAR = 0xB0
    DISC_MENU = 0xA4
    FUNCTION = 0x8A
    GREEN = 0x6D
    HOME = 0xA5
    INFO_MENU = 0xA3
    MUTE = 0x1F
    NAV_DOWN = 0xA6
    NAV_LEFT = 0xA8
    NAV_RIGHT = 0xA9
    NAV_UP = 0xA7
    NUM_0 = 0x4B
    NUM_1 = 0x41
    NUM_2 = 0x42
    NUM_3 = 0x43
    NUM_4 = 0x44
    NUM_5 = 0x45
    NUM_6 = 0x46
    NUM_7 = 0x47
    NUM_8 = 0x48
    NUM_9 = 0x49
    OK = 0xAA
    OPEN_CLOSE = 0x9A
    OPTICAL_TV_SOUND = 0xB6
    PAUSE = 0x4F
    PLAY = 0x04
    POWER = 0x1E
    RECORD = 0x83
    RED = 0x6C
    REPEAT = 0x4E
    SCAN_BACKWARD = 0x53
    SCAN_FORWARD = 0x52
    SKIP_BACKWARD = 0x06
    SKIP_FORWARD = 0x07
    SLEEP = 0xC2
    SOUND_EFFECT = 0x2F
    SPEAKER_LEVEL = 0x66
    STOP = 0x05
    SUBTITLE = 0xAB
    TITLE_POPUP = 0xAF
    VOLUME_DOWN = 0x16
    VOLUME_UP = 0x17
    YELLOW = 0x6E

    def to_command(self, repeat_count: int = 0) -> Command:
        """Build a Samsung32 command for this LG home theater code."""
        return Samsung32Command(
            address=LG_HOME_THEATER_ADDRESS,
            command=self.value,
            repeat_count=repeat_count,
        )

"""Command codes for LG TVs."""

from enum import Enum, IntEnum

from ...commands import Command
from ...commands.nec import NECCommand

LG_ADDRESS = 0xFB04


class LGTVCode(IntEnum):
    """LG TV IR command codes."""

    ASPECT = 0x79
    BACK = 0x28
    BLUE = 0x72
    CHANNEL_DOWN = 0x01
    CHANNEL_UP = 0x00
    EXIT = 0x5B
    EZ_ADJUST = 0xFF
    FAST_FORWARD = 0x8E
    GREEN = 0x63
    GUIDE = 0xA9
    HDMI_1 = 0xCE
    HDMI_2 = 0xCC
    HDMI_3 = 0xE9
    HDMI_4 = 0xDA
    HOME = 0x7C
    INFO = 0xAA
    INPUT = 0x0B
    IN_START = 0xFB
    LIST = 0xCA
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
    RED = 0x71
    REWIND = 0x8F
    SAP = 0x0A
    SETTINGS = 0x45
    STOP = 0xB1
    SUBTITLE = 0x39
    TEXT = 0x20
    VOLUME_DOWN = 0x03
    VOLUME_UP = 0x02
    YELLOW = 0x61

    def to_command(self, repeat_count: int = 0) -> Command:
        """Build an NEC command for this LG TV code."""
        return NECCommand(
            address=LG_ADDRESS, command=self.value, repeat_count=repeat_count
        )


class LGTVCodeJP(Enum):
    """Japan-specific LG TV IR command codes.

    Normal commands store only the command byte. Japan tuner selectors and
    tuner numeric commands store ``(command, subfunction)`` for NEC1-f16.
    """

    AMAZON = 0x5C
    ASPECT = 0x79
    BACK = 0x28
    BLUE = 0x72
    BS = (0xDB, 0x00)
    BS_NUM_1 = (0xDB, 0x01)
    BS_NUM_2 = (0xDB, 0x02)
    BS_NUM_3 = (0xDB, 0x03)
    BS_NUM_4 = (0xDB, 0x04)
    BS_NUM_5 = (0xDB, 0x05)
    BS_NUM_6 = (0xDB, 0x06)
    BS_NUM_7 = (0xDB, 0x07)
    BS_NUM_8 = (0xDB, 0x08)
    BS_NUM_9 = (0xDB, 0x09)
    BS_NUM_10 = (0xDB, 0x0A)
    BS_NUM_11 = (0xDB, 0x0B)
    BS_NUM_12 = (0xDB, 0x0C)
    BS4K = (0xDB, 0x40)
    BS4K_NUM_1 = (0xDB, 0x41)
    BS4K_NUM_2 = (0xDB, 0x42)
    BS4K_NUM_3 = (0xDB, 0x43)
    BS4K_NUM_4 = (0xDB, 0x44)
    BS4K_NUM_5 = (0xDB, 0x45)
    BS4K_NUM_6 = (0xDB, 0x46)
    BS4K_NUM_7 = (0xDB, 0x47)
    BS4K_NUM_8 = (0xDB, 0x48)
    BS4K_NUM_9 = (0xDB, 0x49)
    BS4K_NUM_10 = (0xDB, 0x4A)
    BS4K_NUM_11 = (0xDB, 0x4B)
    BS4K_NUM_12 = (0xDB, 0x4C)
    CS4K = (0xDB, 0x50)
    CS4K_NUM_1 = (0xDB, 0x51)
    CS4K_NUM_2 = (0xDB, 0x52)
    CS4K_NUM_3 = (0xDB, 0x53)
    CS4K_NUM_4 = (0xDB, 0x54)
    CS4K_NUM_5 = (0xDB, 0x55)
    CS4K_NUM_6 = (0xDB, 0x56)
    CS4K_NUM_7 = (0xDB, 0x57)
    CS4K_NUM_8 = (0xDB, 0x58)
    CS4K_NUM_9 = (0xDB, 0x59)
    CS4K_NUM_10 = (0xDB, 0x5A)
    CS4K_NUM_11 = (0xDB, 0x5B)
    CS4K_NUM_12 = (0xDB, 0x5C)
    CHANNEL_DOWN = 0x01
    CHANNEL_UP = 0x00
    CS1 = (0xDB, 0x10)
    CS1_NUM_1 = (0xDB, 0x11)
    CS1_NUM_2 = (0xDB, 0x12)
    CS1_NUM_3 = (0xDB, 0x13)
    CS1_NUM_4 = (0xDB, 0x14)
    CS1_NUM_5 = (0xDB, 0x15)
    CS1_NUM_6 = (0xDB, 0x16)
    CS1_NUM_7 = (0xDB, 0x17)
    CS1_NUM_8 = (0xDB, 0x18)
    CS1_NUM_9 = (0xDB, 0x19)
    CS1_NUM_10 = (0xDB, 0x1A)
    CS1_NUM_11 = (0xDB, 0x1B)
    CS1_NUM_12 = (0xDB, 0x1C)
    CS2 = (0xDB, 0x20)
    CS2_NUM_1 = (0xDB, 0x21)
    CS2_NUM_2 = (0xDB, 0x22)
    CS2_NUM_3 = (0xDB, 0x23)
    CS2_NUM_4 = (0xDB, 0x24)
    CS2_NUM_5 = (0xDB, 0x25)
    CS2_NUM_6 = (0xDB, 0x26)
    CS2_NUM_7 = (0xDB, 0x27)
    CS2_NUM_8 = (0xDB, 0x28)
    CS2_NUM_9 = (0xDB, 0x29)
    CS2_NUM_10 = (0xDB, 0x2A)
    CS2_NUM_11 = (0xDB, 0x2B)
    CS2_NUM_12 = (0xDB, 0x2C)
    DATA = 0xCC
    DTV = (0xDB, 0x30)
    DTV_NUM_1 = (0xDB, 0x31)
    DTV_NUM_2 = (0xDB, 0x32)
    DTV_NUM_3 = (0xDB, 0x33)
    DTV_NUM_4 = (0xDB, 0x34)
    DTV_NUM_5 = (0xDB, 0x35)
    DTV_NUM_6 = (0xDB, 0x36)
    DTV_NUM_7 = (0xDB, 0x37)
    DTV_NUM_8 = (0xDB, 0x38)
    DTV_NUM_9 = (0xDB, 0x39)
    DTV_NUM_10 = (0xDB, 0x3A)
    DTV_NUM_11 = (0xDB, 0x3B)
    DTV_NUM_12 = (0xDB, 0x3C)
    EXIT = 0x5B
    EZ_ADJUST = 0xFF
    FAST_FORWARD = 0x8E
    GREEN = 0x63
    GUIDE = 0xA9
    HDMI_1 = 0xCE
    HDMI_2 = 0x91
    HDMI_3 = 0xD0
    HDMI_4 = 0xD1
    HOME = 0x7C
    INFO = 0xAA
    INPUT = 0x0B
    IN_START = 0xFB
    LIST = 0x53
    MENU = 0x43
    MUTE = 0x09
    NAV_DOWN = 0x05
    NAV_LEFT = 0x07
    NAV_RIGHT = 0x06
    NAV_UP = 0x04
    NETFLIX = 0x56
    NUM_1 = 0x11
    NUM_2 = 0x12
    NUM_3 = 0x13
    NUM_4 = 0x14
    NUM_5 = 0x15
    NUM_6 = 0x16
    NUM_7 = 0x17
    NUM_8 = 0x18
    NUM_9 = 0x19
    NUM_10 = 0x10
    NUM_11 = 0x40
    NUM_12 = 0x41
    OK = 0x44
    PAUSE = 0xBA
    PLAY = 0xB0
    POWER = 0x08
    POWER_ON = 0xC4
    POWER_OFF = 0xC5
    REC_LIST = 0x1E
    RECORD = 0xBD
    RED = 0x71
    REWIND = 0x8F
    SAP = 0x0A
    SETTINGS = 0x45
    STOP = 0xB1
    SUBTITLE = 0x39
    THREE_DIGIT_INPUT = 0x32
    TV = 0x5F
    VOLUME_DOWN = 0x03
    VOLUME_UP = 0x02
    YELLOW = 0x61

    def to_command(self, repeat_count: int = 0) -> Command:
        """Build an NEC command for this Japanese LG TV code."""
        if isinstance(self.value, tuple):
            command, subfunction = self.value
            return NECCommand(
                address=LG_ADDRESS,
                command=command,
                subfunction=subfunction,
                repeat_count=repeat_count,
            )

        return NECCommand(
            address=LG_ADDRESS,
            command=self.value,
            repeat_count=repeat_count,
        )

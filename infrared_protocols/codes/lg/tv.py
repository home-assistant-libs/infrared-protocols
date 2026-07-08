"""Command codes for LG TVs."""

from dataclasses import dataclass
from enum import Enum, IntEnum

from ...commands import Command
from ...commands.nec import NECCommand
from ...commands.nec1_f16 import NEC1F16Command

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


@dataclass(frozen=True, slots=True, eq=False)
class _NECCode:
    """Normal NEC command code spec."""

    address: int
    command: int

    def to_command(self, repeat_count: int = 0) -> Command:
        """Build an NEC command."""
        return NECCommand(
            address=self.address,
            command=self.command,
            repeat_count=repeat_count,
        )


@dataclass(frozen=True, slots=True, eq=False)
class _NEC1F16Code:
    """NEC1-F16 command code spec."""

    address: int
    function: int
    subfunction: int

    def to_command(self, repeat_count: int = 0) -> Command:
        """Build an NEC1-F16 command."""
        return NEC1F16Command(
            address=self.address,
            function=self.function,
            subfunction=self.subfunction,
            repeat_count=repeat_count,
        )


class LGTVCodeJP(Enum):
    """Japan-specific LG TV IR command codes.

    Normal commands are encoded as NEC commands. Japan tuner selectors and
    tuner numeric commands are encoded as NEC1-f16 commands using explicit
    ``address, function, subfunction`` values.
    """

    AMAZON = _NECCode(0xFB04, 0x5C)
    ASPECT = _NECCode(0xFB04, 0x79)
    BACK = _NECCode(0xFB04, 0x28)
    BLUE = _NECCode(0xFB04, 0x72)
    BS = _NEC1F16Code(0xFB04, 0xDB, 0x00)
    BS_NUM_1 = _NEC1F16Code(0xFB04, 0xDB, 0x01)
    BS_NUM_2 = _NEC1F16Code(0xFB04, 0xDB, 0x02)
    BS_NUM_3 = _NEC1F16Code(0xFB04, 0xDB, 0x03)
    BS_NUM_4 = _NEC1F16Code(0xFB04, 0xDB, 0x04)
    BS_NUM_5 = _NEC1F16Code(0xFB04, 0xDB, 0x05)
    BS_NUM_6 = _NEC1F16Code(0xFB04, 0xDB, 0x06)
    BS_NUM_7 = _NEC1F16Code(0xFB04, 0xDB, 0x07)
    BS_NUM_8 = _NEC1F16Code(0xFB04, 0xDB, 0x08)
    BS_NUM_9 = _NEC1F16Code(0xFB04, 0xDB, 0x09)
    BS_NUM_10 = _NEC1F16Code(0xFB04, 0xDB, 0x0A)
    BS_NUM_11 = _NEC1F16Code(0xFB04, 0xDB, 0x0B)
    BS_NUM_12 = _NEC1F16Code(0xFB04, 0xDB, 0x0C)
    BS4K = _NEC1F16Code(0xFB04, 0xDB, 0x40)
    BS4K_NUM_1 = _NEC1F16Code(0xFB04, 0xDB, 0x41)
    BS4K_NUM_2 = _NEC1F16Code(0xFB04, 0xDB, 0x42)
    BS4K_NUM_3 = _NEC1F16Code(0xFB04, 0xDB, 0x43)
    BS4K_NUM_4 = _NEC1F16Code(0xFB04, 0xDB, 0x44)
    BS4K_NUM_5 = _NEC1F16Code(0xFB04, 0xDB, 0x45)
    BS4K_NUM_6 = _NEC1F16Code(0xFB04, 0xDB, 0x46)
    BS4K_NUM_7 = _NEC1F16Code(0xFB04, 0xDB, 0x47)
    BS4K_NUM_8 = _NEC1F16Code(0xFB04, 0xDB, 0x48)
    BS4K_NUM_9 = _NEC1F16Code(0xFB04, 0xDB, 0x49)
    BS4K_NUM_10 = _NEC1F16Code(0xFB04, 0xDB, 0x4A)
    BS4K_NUM_11 = _NEC1F16Code(0xFB04, 0xDB, 0x4B)
    BS4K_NUM_12 = _NEC1F16Code(0xFB04, 0xDB, 0x4C)
    CS4K = _NEC1F16Code(0xFB04, 0xDB, 0x50)
    CS4K_NUM_1 = _NEC1F16Code(0xFB04, 0xDB, 0x51)
    CS4K_NUM_2 = _NEC1F16Code(0xFB04, 0xDB, 0x52)
    CS4K_NUM_3 = _NEC1F16Code(0xFB04, 0xDB, 0x53)
    CS4K_NUM_4 = _NEC1F16Code(0xFB04, 0xDB, 0x54)
    CS4K_NUM_5 = _NEC1F16Code(0xFB04, 0xDB, 0x55)
    CS4K_NUM_6 = _NEC1F16Code(0xFB04, 0xDB, 0x56)
    CS4K_NUM_7 = _NEC1F16Code(0xFB04, 0xDB, 0x57)
    CS4K_NUM_8 = _NEC1F16Code(0xFB04, 0xDB, 0x58)
    CS4K_NUM_9 = _NEC1F16Code(0xFB04, 0xDB, 0x59)
    CS4K_NUM_10 = _NEC1F16Code(0xFB04, 0xDB, 0x5A)
    CS4K_NUM_11 = _NEC1F16Code(0xFB04, 0xDB, 0x5B)
    CS4K_NUM_12 = _NEC1F16Code(0xFB04, 0xDB, 0x5C)
    CHANNEL_DOWN = _NECCode(0xFB04, 0x01)
    CHANNEL_UP = _NECCode(0xFB04, 0x00)
    CS1 = _NEC1F16Code(0xFB04, 0xDB, 0x10)
    CS1_NUM_1 = _NEC1F16Code(0xFB04, 0xDB, 0x11)
    CS1_NUM_2 = _NEC1F16Code(0xFB04, 0xDB, 0x12)
    CS1_NUM_3 = _NEC1F16Code(0xFB04, 0xDB, 0x13)
    CS1_NUM_4 = _NEC1F16Code(0xFB04, 0xDB, 0x14)
    CS1_NUM_5 = _NEC1F16Code(0xFB04, 0xDB, 0x15)
    CS1_NUM_6 = _NEC1F16Code(0xFB04, 0xDB, 0x16)
    CS1_NUM_7 = _NEC1F16Code(0xFB04, 0xDB, 0x17)
    CS1_NUM_8 = _NEC1F16Code(0xFB04, 0xDB, 0x18)
    CS1_NUM_9 = _NEC1F16Code(0xFB04, 0xDB, 0x19)
    CS1_NUM_10 = _NEC1F16Code(0xFB04, 0xDB, 0x1A)
    CS1_NUM_11 = _NEC1F16Code(0xFB04, 0xDB, 0x1B)
    CS1_NUM_12 = _NEC1F16Code(0xFB04, 0xDB, 0x1C)
    CS2 = _NEC1F16Code(0xFB04, 0xDB, 0x20)
    CS2_NUM_1 = _NEC1F16Code(0xFB04, 0xDB, 0x21)
    CS2_NUM_2 = _NEC1F16Code(0xFB04, 0xDB, 0x22)
    CS2_NUM_3 = _NEC1F16Code(0xFB04, 0xDB, 0x23)
    CS2_NUM_4 = _NEC1F16Code(0xFB04, 0xDB, 0x24)
    CS2_NUM_5 = _NEC1F16Code(0xFB04, 0xDB, 0x25)
    CS2_NUM_6 = _NEC1F16Code(0xFB04, 0xDB, 0x26)
    CS2_NUM_7 = _NEC1F16Code(0xFB04, 0xDB, 0x27)
    CS2_NUM_8 = _NEC1F16Code(0xFB04, 0xDB, 0x28)
    CS2_NUM_9 = _NEC1F16Code(0xFB04, 0xDB, 0x29)
    CS2_NUM_10 = _NEC1F16Code(0xFB04, 0xDB, 0x2A)
    CS2_NUM_11 = _NEC1F16Code(0xFB04, 0xDB, 0x2B)
    CS2_NUM_12 = _NEC1F16Code(0xFB04, 0xDB, 0x2C)
    DATA = _NECCode(0xFB04, 0xCC)
    DTV = _NEC1F16Code(0xFB04, 0xDB, 0x30)
    DTV_NUM_1 = _NEC1F16Code(0xFB04, 0xDB, 0x31)
    DTV_NUM_2 = _NEC1F16Code(0xFB04, 0xDB, 0x32)
    DTV_NUM_3 = _NEC1F16Code(0xFB04, 0xDB, 0x33)
    DTV_NUM_4 = _NEC1F16Code(0xFB04, 0xDB, 0x34)
    DTV_NUM_5 = _NEC1F16Code(0xFB04, 0xDB, 0x35)
    DTV_NUM_6 = _NEC1F16Code(0xFB04, 0xDB, 0x36)
    DTV_NUM_7 = _NEC1F16Code(0xFB04, 0xDB, 0x37)
    DTV_NUM_8 = _NEC1F16Code(0xFB04, 0xDB, 0x38)
    DTV_NUM_9 = _NEC1F16Code(0xFB04, 0xDB, 0x39)
    DTV_NUM_10 = _NEC1F16Code(0xFB04, 0xDB, 0x3A)
    DTV_NUM_11 = _NEC1F16Code(0xFB04, 0xDB, 0x3B)
    DTV_NUM_12 = _NEC1F16Code(0xFB04, 0xDB, 0x3C)
    EXIT = _NECCode(0xFB04, 0x5B)
    EZ_ADJUST = _NECCode(0xFB04, 0xFF)
    FAST_FORWARD = _NECCode(0xFB04, 0x8E)
    GREEN = _NECCode(0xFB04, 0x63)
    GUIDE = _NECCode(0xFB04, 0xA9)
    HDMI_1 = _NECCode(0xFB04, 0xCE)
    HDMI_2 = _NECCode(0xFB04, 0x91)
    HDMI_3 = _NECCode(0xFB04, 0xD0)
    HDMI_4 = _NECCode(0xFB04, 0xD1)
    HOME = _NECCode(0xFB04, 0x7C)
    INFO = _NECCode(0xFB04, 0xAA)
    INPUT = _NECCode(0xFB04, 0x0B)
    IN_START = _NECCode(0xFB04, 0xFB)
    LIST = _NECCode(0xFB04, 0x53)
    MENU = _NECCode(0xFB04, 0x43)
    MUTE = _NECCode(0xFB04, 0x09)
    NAV_DOWN = _NECCode(0xFB04, 0x05)
    NAV_LEFT = _NECCode(0xFB04, 0x07)
    NAV_RIGHT = _NECCode(0xFB04, 0x06)
    NAV_UP = _NECCode(0xFB04, 0x04)
    NETFLIX = _NECCode(0xFB04, 0x56)
    NUM_1 = _NECCode(0xFB04, 0x11)
    NUM_2 = _NECCode(0xFB04, 0x12)
    NUM_3 = _NECCode(0xFB04, 0x13)
    NUM_4 = _NECCode(0xFB04, 0x14)
    NUM_5 = _NECCode(0xFB04, 0x15)
    NUM_6 = _NECCode(0xFB04, 0x16)
    NUM_7 = _NECCode(0xFB04, 0x17)
    NUM_8 = _NECCode(0xFB04, 0x18)
    NUM_9 = _NECCode(0xFB04, 0x19)
    NUM_10 = _NECCode(0xFB04, 0x10)
    NUM_11 = _NECCode(0xFB04, 0x40)
    NUM_12 = _NECCode(0xFB04, 0x41)
    OK = _NECCode(0xFB04, 0x44)
    PAUSE = _NECCode(0xFB04, 0xBA)
    PLAY = _NECCode(0xFB04, 0xB0)
    POWER = _NECCode(0xFB04, 0x08)
    POWER_ON = _NECCode(0xFB04, 0xC4)
    POWER_OFF = _NECCode(0xFB04, 0xC5)
    REC_LIST = _NECCode(0xFB04, 0x1E)
    RECORD = _NECCode(0xFB04, 0xBD)
    RED = _NECCode(0xFB04, 0x71)
    REWIND = _NECCode(0xFB04, 0x8F)
    SAP = _NECCode(0xFB04, 0x0A)
    SETTINGS = _NECCode(0xFB04, 0x45)
    STOP = _NECCode(0xFB04, 0xB1)
    SUBTITLE = _NECCode(0xFB04, 0x39)
    THREE_DIGIT_INPUT = _NECCode(0xFB04, 0x32)
    TV = _NECCode(0xFB04, 0x5F)
    VOLUME_DOWN = _NECCode(0xFB04, 0x03)
    VOLUME_UP = _NECCode(0xFB04, 0x02)
    YELLOW = _NECCode(0xFB04, 0x61)

    def to_command(self, repeat_count: int = 0) -> Command:
        """Build an infrared command for this Japanese LG TV code."""
        return self.value.to_command(repeat_count=repeat_count)

"""Command codes for Vizio TVs."""

from enum import IntEnum

from ...commands import Command
from ...commands.nec import NECCommand

VIZIO_ADDRESS = 0x04


class VizioTVCode(IntEnum):
    """Vizio TV IR command codes."""

    CHANNEL_UP = 0x00
    CHANNEL_DOWN = 0x01
    VOLUME_UP = 0x02
    VOLUME_DOWN = 0x03
    POWER = 0x08
    POWER_ON = 0x2A
    POWER_OFF = 0x25
    MUTE = 0x09
    MUTE_ON = 0x20
    MUTE_OFF = 0x21

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
    LAST_CHANNEL = 0x1A
    CHANNEL_DASH = 0xFF
    INFO = 0x1B
    GUIDE = 0x1C
    LIST = 0x1D

    STOP = 0x30
    PLAY = 0x33
    RECORD = 0x34
    REWIND = 0x35
    FAST_FORWARD = 0x36
    PAUSE = 0x37
    EXIT = 0x39
    ENTER = 0x3A

    OK = 0x44
    NAV_UP = 0x45
    NAV_DOWN = 0x46
    NAV_LEFT = 0x47
    NAV_RIGHT = 0x48
    EXIT_ALT = 0x49
    BACK = 0x4A
    MENU = 0x4F

    YELLOW = 0x52
    BLUE = 0x53
    RED = 0x54
    GREEN = 0x55

    HOME = 0x2D
    INPUT = 0x2F
    HDMI_1 = 0x81
    HDMI_2 = 0x82
    HDMI_3 = 0x83
    HDMI_4 = 0x84
    HDMI_5 = 0x85
    NEXT_HDMI_INPUT = 0xC6
    COMPONENT_INPUT = 0x5A
    COMPONENT_INPUT_ALT = 0xA1
    TV_INPUT = 0xD6
    INPUT_UNKNOWN_71 = 0x71
    INPUT_UNKNOWN_72 = 0x72
    INPUT_UNKNOWN_98 = 0x98

    SLEEP_TIMER = 0x0E
    PICTURE_MODE = 0x67
    ASPECT_MENU = 0x77
    THREE_D = 0x90

    DPAD_UP = 0xE2
    DPAD_DOWN = 0xE3
    DPAD_LEFT = 0xE4
    DPAD_RIGHT = 0xE5
    MEDIA_PLAYER = 0xF0
    OK_ALT = 0xFE

    KEY_LOWER_Q = 0x04
    KEY_LOWER_W = 0x05
    KEY_LOWER_E = 0x0B
    KEY_LOWER_R = 0x0C
    KEY_LOWER_T = 0x0D
    KEY_LOWER_Y = 0x0F
    KEY_LOWER_U = 0x29
    KEY_LOWER_I = 0x57
    KEY_LOWER_O = 0x58
    KEY_LOWER_P = 0x59
    KEY_LOWER_A = 0x5B
    KEY_LOWER_S = 0x5C
    KEY_LOWER_D = 0x5D
    KEY_LOWER_F = 0x5E
    KEY_LOWER_G = 0x5F
    KEY_LOWER_H = 0x68
    KEY_LOWER_J = 0x69
    KEY_LOWER_K = 0x6A
    KEY_LOWER_L = 0x6B
    KEY_LOWER_Z = 0x6C
    KEY_LOWER_X = 0x6D
    KEY_LOWER_C = 0x6E
    KEY_LOWER_V = 0x70
    KEY_LOWER_B = 0x75
    KEY_LOWER_N = 0x76
    KEY_LOWER_M = 0x78

    KEY_UPPER_Q = 0x79
    KEY_UPPER_W = 0x7A
    KEY_UPPER_E = 0x7B
    KEY_UPPER_R = 0x7C
    KEY_UPPER_T = 0x7D
    KEY_UPPER_Y = 0x7E
    KEY_UPPER_U = 0x7F
    KEY_UPPER_I = 0x89
    KEY_UPPER_O = 0x8A
    KEY_UPPER_P = 0x8B
    KEY_UPPER_A = 0x8C
    KEY_UPPER_S = 0x8D
    KEY_UPPER_D = 0x8E
    KEY_UPPER_F = 0x8F
    KEY_UPPER_G = 0x93
    KEY_UPPER_H = 0x94
    KEY_UPPER_J = 0x95
    KEY_UPPER_K = 0x96
    KEY_UPPER_L = 0x97
    KEY_UPPER_Z = 0x99
    KEY_UPPER_X = 0x9A
    KEY_UPPER_C = 0x9B
    KEY_UPPER_V = 0x9C
    KEY_UPPER_B = 0x9D
    KEY_UPPER_N = 0x9E
    KEY_UPPER_M = 0x9F

    KEY_EQUALS = 0xA5
    KEY_SEMICOLON = 0xA6
    KEY_COMMA = 0xA7
    KEY_PERIOD = 0xA8
    KEY_AT = 0xA9
    KEY_EXCLAMATION = 0xAA
    KEY_HASH = 0xAB
    KEY_DOLLAR = 0xAC
    KEY_PERCENT = 0xAD
    KEY_CARET = 0xAE
    KEY_AMPERSAND = 0xAF

    KEY_RIGHT_BRACKET = 0xC0
    KEY_LEFT_PAREN = 0xC1
    KEY_RIGHT_PAREN = 0xC2
    KEY_BACKSLASH = 0xC3
    KEY_PLUS = 0xC4
    KEY_SINGLE_QUOTE = 0xC7
    KEY_DOUBLE_QUOTE = 0xC8
    KEY_UNDERSCORE = 0xC9
    KEY_SPACE_ALT = 0xCC

    KEY_SPACE = 0xD0
    KEY_ASTERISK = 0xD1
    KEY_TILDE = 0xD2
    KEY_QUESTION = 0xD3
    KEY_HYPHEN = 0xD4
    KEY_LESS_THAN = 0xD5
    KEY_GREATER_THAN = 0xD7
    KEY_LEFT_BRACKET = 0xD8
    KEY_COLON = 0xD9
    KEY_DOT_COM = 0xDA
    KEY_SLASH = 0xDE

    XUMO = 0x6F
    AMAZON_PRIME = 0xEA
    NETFLIX = 0xEB
    VUDU = 0xEC
    MGO = 0xED
    IHEARTRADIO = 0xEE
    WATCHFREE = 0xF7
    CRACKLE = 0xF8
    HULU = 0xF9

    def to_command(self, repeat_count: int = 0) -> Command:
        """Build an NEC command for this Vizio TV code."""
        return NECCommand(
            address=VIZIO_ADDRESS,
            command=self.value,
            repeat_count=repeat_count,
        )

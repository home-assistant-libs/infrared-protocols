"""Command codes for BenQ projectors.

Codes are taken from the IR code list in BenQ's projector service manuals and
from Flipper-IRDB and IRDB captures of BenQ projector remotes. All BenQ
projectors share one extended NEC address; BenQ calls it custom code 0x30.

Not every projector responds to every code. The service manual marks per model
which codes are supported, and newer home cinema keys (HDR, LumiExpert, sound
mode and the media keys) are only known from captures.
"""

from enum import IntEnum, unique

from ...commands import Command
from ...commands.nec import NECCommand

BENQ_PROJECTOR_ADDRESS = 0x3000


@unique
class BenQProjectorCode(IntEnum):
    """BenQ projector IR command codes."""

    POWER = 0x02
    POWER_OFF = 0x4E
    POWER_ON = 0x4F

    SOURCE = 0x04
    PC_1 = 0x41
    PC_2 = 0x45
    RGBHV = 0x40
    DVI_D = 0x42
    DVI_A = 0x43
    DVI_I = 0x44
    COMPONENT_1 = 0x51
    COMPONENT_2 = 0x50
    VIDEO_1 = 0x52
    VIDEO_2 = 0x53
    S_VIDEO_1 = 0x1F
    S_VIDEO_2 = 0x54
    HDMI_1 = 0x58
    HDMI_2 = 0x59
    NETWORK_DISPLAY = 0x46
    USB_DISPLAY = 0x47
    USB_READER = 0x48
    WIRELESS = 0x86

    UP = 0x0B
    DOWN = 0x0C
    LEFT = 0x0D
    RIGHT = 0x0E
    ENTER = 0x15
    MENU = 0x0F
    BACK = 0x85
    RETURN = 0x92
    INFO = 0x2B

    MUTE = 0x14
    VOLUME_UP = 0x82
    VOLUME_DOWN = 0x83
    AUDIO = 0x1A
    SOUND_MODE = 0x3D
    SRS = 0x99
    MIC_VOLUME_UP = 0x97
    MIC_VOLUME_DOWN = 0x98

    PICTURE_MODE = 0x10
    PICTURE = 0x2F
    USER_1 = 0x75
    USER_2 = 0x76
    USER_3 = 0x77
    DEFAULT = 0x78
    BRIGHTNESS = 0x16
    CONTRAST = 0x11
    COLOR = 0x79
    TINT = 0x7A
    SHARPNESS = 0x7E
    GAMMA = 0x5E
    COLOR_TEMPERATURE = 0x5F
    COLOR_MANAGEMENT = 0x5B
    BRILLIANT_COLOR = 0x7D
    DETAIL_ENHANCEMENT = 0x5A
    FINE_TUNE = 0x5D
    CINEMA_MASTER = 0xBE
    DYNAMIC_IRIS = 0x7C
    HDR = 0x3C
    LUMIEXPERT = 0x3B
    LIGHT_MODE = 0x30  # Smart Eco on business models
    ECO_BLANK = 0x07
    FREEZE = 0x03
    AUTO = 0x08
    OVERSCAN = 0x7F

    ASPECT = 0x13
    ASPECT_ANAMORPHIC = 0x70
    ASPECT_4_3 = 0x71
    ASPECT_LETTERBOX = 0x72
    ASPECT_WIDE = 0x73
    ASPECT_REAL = 0x74

    KEYSTONE_UP = 0x09
    KEYSTONE_DOWN = 0x0A
    KEYSTONE_2D = 0x2A
    KEYSTONE_VERTICAL = 0x8E
    KEYSTONE_HORIZONTAL = 0x8F
    DIGITAL_ZOOM_IN = 0x18
    DIGITAL_ZOOM_OUT = 0x19
    PAN = 0x88
    LENS = 0x8A
    FOCUS = 0x8B
    ZOOM = 0x8C
    TEST_PATTERN = 0x94  # Quick Install on business models

    THREE_D = 0x8D
    THREE_D_MENU = 0x9C
    THREE_D_SYNC_INVERT = 0x9D

    PIP = 0x1B
    POP = 0x1C
    PAP = 0x1D
    PIP_SIZE = 0x90
    PIP_POSITION = 0x91
    SWAP = 0x12
    SPLIT_SCREEN_ON = 0x95
    SPLIT_SCREEN_OFF = 0x96

    PLAY = 0xA9
    PAUSE = 0xA8
    STOP = 0xAA
    PREVIOUS = 0xA6
    NEXT = 0xA7
    REWIND = 0xA4
    FAST_FORWARD = 0xA5

    PAGE_UP = 0x05
    PAGE_DOWN = 0x06
    MOUSE_LEFT = 0x9E
    MOUSE_RIGHT = 0x9F
    CAPTURE = 0x1E
    MY_SCREEN = 0x93
    TEACHING_TEMPLATE = 0x9B
    CLOSED_CAPTION = 0x9A
    TIMER_ON = 0x25
    TIMER_SETUP = 0x26
    KEY_LOCK = 0x87
    NETWORK_SETTING = 0x81
    WIRELESS_CHANNEL = 0x17
    ID_SET = 0x2E
    ALL_CLEAR = 0x2C

    USB_SETTING = 0x60
    USB_UP = 0x61
    USB_DOWN = 0x62
    USB_LEFT = 0x63
    USB_RIGHT = 0x64
    USB_SELECT = 0x65
    USB_RETURN = 0x66

    IPHONE_PLAY_PAUSE = 0x21
    IPHONE_NEXT = 0x22
    IPHONE_PREVIOUS = 0x23
    IPHONE_MENU = 0x24
    IPHONE_SCROLL_UP = 0x27
    IPHONE_SCROLL_DOWN = 0x28
    IPHONE_OK = 0x29

    NUM_0 = 0x3A
    NUM_1 = 0x31
    NUM_2 = 0x32
    NUM_3 = 0x33
    NUM_4 = 0x34
    NUM_5 = 0x35
    NUM_6 = 0x36
    NUM_7 = 0x37
    NUM_8 = 0x38
    NUM_9 = 0x39

    def to_command(self) -> Command:
        """Build an NEC command for this BenQ projector code."""
        return NECCommand(address=BENQ_PROJECTOR_ADDRESS, command=self.value)

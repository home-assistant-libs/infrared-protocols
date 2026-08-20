"""Command codes for NEC displays.

The same command set drives NEC projectors and televisions. Codes are taken
from an RU-M124 projector remote; the power, standby, digit, navigation,
volume, channel, menu and guide keys are confirmed against a second NEC
television remote.
"""

from enum import IntEnum

from ...commands import Command
from ...commands.proton import ProtonCommand

NEC_DISPLAY_ADDRESS = 0xF4


class NECDisplayCode(IntEnum):
    """NEC display IR command codes."""

    POWER = 0x52
    STANDBY = 0x4E
    MUTE = 0x1B
    VOLUME_UP = 0x17
    VOLUME_DOWN = 0x16

    NUM_0 = 0x12
    NUM_1 = 0x08
    NUM_2 = 0x09
    NUM_3 = 0x0A
    NUM_4 = 0x0B
    NUM_5 = 0x0C
    NUM_6 = 0x0D
    NUM_7 = 0x0E
    NUM_8 = 0x0F
    NUM_9 = 0x10

    CHANNEL_UP = 0x33
    CHANNEL_DOWN = 0x32

    NAV_UP = 0x15
    NAV_DOWN = 0x14
    NAV_LEFT = 0x22
    NAV_RIGHT = 0x21
    OK = 0x23
    ENTER = 0x45
    MENU = 0x20
    EXIT = 0x1F
    GUIDE = 0x34
    OPTION = 0x39
    OPTION_MENU = 0x56
    DISPLAY = 0x19
    TEXT = 0x2C

    INPUT_VGA = 0x04
    INPUT_DVI = 0x2D
    INPUT_HDMI_1 = 0x64
    INPUT_HDMI_2 = 0x58
    INPUT_HDMI_3 = 0x59
    INPUT_DISPLAYPORT_1 = 0x66
    INPUT_DISPLAYPORT_2 = 0x67
    INPUT_VIDEO = 0x53
    INPUT_MEDIA_PLAYER = 0x68
    INPUT_COMPUTE_MODULE = 0x69
    AUDIO_INPUT = 0x1E

    PICTURE_MODE = 0x1D
    ASPECT_RATIO = 0x29
    AUTO_SETUP = 0x1C
    IMAGE_FLIP = 0x57
    STILL = 0x27
    CAPTURE = 0x28
    MULTI_PICTURE = 0x24
    ACTIVE_PICTURE = 0x5F
    MTS = 0x1A

    def to_command(self) -> Command:
        """Build a Proton command for this NEC display code."""
        return ProtonCommand(address=NEC_DISPLAY_ADDRESS, command=self.value)

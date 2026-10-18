"""Command codes for NAD AV receivers.

Codes are taken from NAD's "IR Commands by Model" tables (April 2012), which
list the same set for the T187, T777 and T787. They are sent on IR channel 0;
other IR channels use a non-NEC variant of the frame.
"""

from enum import IntEnum

from ...commands import Command
from ...commands.nec import NECCommand

# NAD documents the customer code as 877C: first byte 0x87, second byte 0x7C.
NAD_RECEIVER_ADDRESS = 0x7C87


class NADReceiverCode(IntEnum):
    """NAD AV receiver IR command codes."""

    AM = 0x82
    AUDYSSEY = 0xC9
    AV_PRESET_1 = 0x3A
    AV_PRESET_2 = 0x3B
    AV_PRESET_3 = 0xC3
    AV_PRESET_4 = 0xC4
    AV_PRESET_5 = 0xC6
    BYPASS = 0xDB
    CENTER_VOLUME_DOWN = 0xD5
    CENTER_VOLUME_UP = 0xD0
    CURSOR_DOWN = 0x28
    CURSOR_LEFT = 0x29
    CURSOR_RIGHT = 0x2A
    CURSOR_UP = 0x27
    DB_XM_DAB = 0x7E
    DELAY = 0xDA
    DIMMER = 0x38
    DIRECT = 0x64
    DISPLAY = 0x26
    DOLBY_SURROUND_EX = 0x69
    EARS = 0x6F
    ENHANCED_STEREO_1 = 0x70
    ENTER = 0x32
    FM = 0x81
    FRONT = 0x85
    INPUT_1 = 0xC2
    INPUT_2 = 0xC0
    INPUT_3 = 0xC1
    INPUT_4 = 0x30
    INPUT_5 = 0x31
    INPUT_6 = 0x1E
    INPUT_7 = 0x60
    LATE_NIGHT = 0x2F
    MATRIX_7_1 = 0x6E
    MEMORY = 0xF5
    MP = 0x89
    MUTE = 0x94
    NEO6_CINEMA = 0x6C
    NEO6_MUSIC = 0x6D
    OFF = 0xC8
    ON = 0x25
    PLIIX_MOVIE = 0x6B
    PLIIX_MUSIC = 0x6A
    POWER_TOGGLE = 0x80
    PRESET_DOWN = 0xD1
    PRESET_UP = 0xD2
    SEARCH_DOWN = 0x86
    SEARCH_UP = 0x87
    SLEEP = 0x20
    SPEAKER_A = 0xCE
    SPEAKER_B = 0xCF
    STEREO_DOWNMIX = 0x65
    SUB_VOLUME_DOWN = 0xD9
    SUB_VOLUME_UP = 0xD8
    SURROUND_MODE = 0xCC
    SURROUND_VOLUME_DOWN = 0xD7
    SURROUND_VOLUME_UP = 0xD6
    TEST = 0xCD
    TONE = 0x39
    TONE_DEFEAT = 0xDC
    TUNER = 0xDD
    TUNER_1 = 0x8A
    TUNER_2 = 0x8E
    TUNER_3 = 0x92
    TUNER_4 = 0x96
    TUNER_5 = 0x8B
    TUNER_6 = 0x8F
    TUNER_7 = 0x93
    TUNER_8 = 0x97
    TUNER_9 = 0x98
    TUNER_ENTER = 0xC5
    TUNER_MODE = 0x37
    TUNE_DOWN = 0xD3
    TUNE_UP = 0xD4
    VOLUME_DOWN = 0x8C
    VOLUME_UP = 0x88
    ZONE_AM = 0xA1
    ZONE_CD = 0xA5
    ZONE_DISC = 0xA6
    ZONE_FM = 0xA2
    ZONE_LOCAL = 0xB3
    ZONE_MUTE = 0xA0
    ZONE_POWER_OFF = 0xB1
    ZONE_POWER_ON = 0xB0
    ZONE_POWER_TOGGLE = 0xB4
    ZONE_PRESET_DOWN = 0xA4
    ZONE_PRESET_UP = 0xA3
    ZONE_SEARCH_DOWN = 0xB8
    ZONE_SEARCH_UP = 0xB7
    ZONE_SOURCE_DOWN = 0xBB
    ZONE_SOURCE_UP = 0xBA
    ZONE_TUNER = 0xAF
    ZONE_TUNE_DOWN = 0xB6
    ZONE_TUNE_UP = 0xB5
    ZONE_VIDEO_1_DVD = 0xA8
    ZONE_VIDEO_2_SAT = 0xA9
    ZONE_VIDEO_3_VCR = 0xAA
    ZONE_VIDEO_4 = 0xAB
    ZONE_VIDEO_5 = 0xAC
    ZONE_VIDEO_6 = 0xAD

    def to_command(self) -> Command:
        """Build an NEC command for this NAD receiver code."""
        return NECCommand(address=NAD_RECEIVER_ADDRESS, command=self.value)

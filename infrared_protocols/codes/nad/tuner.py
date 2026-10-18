"""Command codes for NAD tuners.

Codes are taken from NAD's "IR Commands by Model" tables and the IRDB. The
built-in tuner of NAD receivers and standalone NAD tuners respond to the same
codes. All NAD components share one NEC address.

DELETE is captured from a NAD AVR 4 remote.
"""

from enum import IntEnum

from ...commands import Command
from ...commands.nec import NECCommand

NAD_TUNER_ADDRESS = 0x7C87


class NADTunerCode(IntEnum):
    """NAD tuner IR command codes."""

    AM = 0x82
    FM = 0x81
    DAB = 0x7E  # XM satellite radio on North American models
    MODE = 0x37
    TUNE_UP = 0xD4
    TUNE_DOWN = 0xD3
    SEARCH_UP = 0x87
    SEARCH_DOWN = 0x86
    PRESET_UP = 0xD2
    PRESET_DOWN = 0xD1
    PRESET_TUNE = 0x33
    MEMORY = 0xF5
    DELETE = 0xF6
    BANK = 0x24
    BLEND = 0x35
    ENTER = 0xC5

    NUM_0 = 0xC7
    NUM_1 = 0x8A
    NUM_2 = 0x8E
    NUM_3 = 0x92
    NUM_4 = 0x96
    NUM_5 = 0x8B
    NUM_6 = 0x8F
    NUM_7 = 0x93
    NUM_8 = 0x97
    NUM_9 = 0x98
    NUM_10 = 0xF2
    PLUS_10 = 0xF3

    def to_command(self) -> Command:
        """Build an NEC command for this NAD tuner code."""
        return NECCommand(address=NAD_TUNER_ADDRESS, command=self.value)

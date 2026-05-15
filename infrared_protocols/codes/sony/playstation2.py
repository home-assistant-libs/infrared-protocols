"""Command codes for Sony PlayStation 2 (SCPH-XXXXX).

Based on the following remote control models:
- SCPH-10150
- SCPH-10420

Supported PS2 models:
- SCPH-1X000 to SCPH-3X0XX (needs SCPH-10160 IR receiver)
- SCPH-5X00X
- SCPH-7X0XX to SCPH-900XX (does not support Open/Close disc tray command)

For PSX (DESR-XXXX) models, see psx.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ...commands import Command
from ...commands.sony import SonyCommand

_DVD_ADDRESS = 0x1A49
_PS2_ADDRESS = 0x1ADA


class SonyPlayStation2Code(Enum):
    """Sony PlayStation 2 IR command codes.

    All codes use 20-bit SONY SIRC (address_bits=13).

    DVD playback buttons share address 0x1A49 (device=26, subdevice=73).
    PS2 console/pad buttons share address 0x1ADA (device=26, subdevice=218).

    Values are (address, command) pairs.
    """

    # DVD playback buttons (not for PSX models)
    DVD_1 = (_DVD_ADDRESS, 0)
    DVD_2 = (_DVD_ADDRESS, 1)
    DVD_3 = (_DVD_ADDRESS, 2)
    DVD_4 = (_DVD_ADDRESS, 3)
    DVD_5 = (_DVD_ADDRESS, 4)
    DVD_6 = (_DVD_ADDRESS, 5)
    DVD_7 = (_DVD_ADDRESS, 6)
    DVD_8 = (_DVD_ADDRESS, 7)
    DVD_9 = (_DVD_ADDRESS, 8)
    DVD_0 = (_DVD_ADDRESS, 9)
    DVD_ENTER = (_DVD_ADDRESS, 11)
    DVD_RETURN = (_DVD_ADDRESS, 14)
    DVD_CLEAR = (_DVD_ADDRESS, 15)
    DVD_TITLE = (_DVD_ADDRESS, 26)
    DVD_MENU = (_DVD_ADDRESS, 27)
    DVD_PROGRAM = (_DVD_ADDRESS, 31)
    DVD_TIME = (_DVD_ADDRESS, 40)
    DVD_ATOB = (_DVD_ADDRESS, 42)
    DVD_REPEAT = (_DVD_ADDRESS, 44)
    DVD_PREV = (_DVD_ADDRESS, 48)
    DVD_NEXT = (_DVD_ADDRESS, 49)
    DVD_PLAY = (_DVD_ADDRESS, 50)
    DVD_SCAN_BACK = (_DVD_ADDRESS, 51)
    DVD_SCAN_FORW = (_DVD_ADDRESS, 52)
    DVD_SHUFFLE = (_DVD_ADDRESS, 53)
    DVD_STOP = (_DVD_ADDRESS, 56)
    DVD_PAUSE = (_DVD_ADDRESS, 57)
    DVD_DISPLAY = (_DVD_ADDRESS, 84)
    DVD_SLOW_BACK = (_DVD_ADDRESS, 96)
    DVD_SLOW_FORW = (_DVD_ADDRESS, 97)
    DVD_SUBTITLE = (_DVD_ADDRESS, 99)
    DVD_AUDIO = (_DVD_ADDRESS, 100)
    DVD_ANGLE = (_DVD_ADDRESS, 101)
    DVD_UP = (_DVD_ADDRESS, 121)
    DVD_DOWN = (_DVD_ADDRESS, 122)
    DVD_LEFT = (_DVD_ADDRESS, 123)
    DVD_RIGHT = (_DVD_ADDRESS, 124)

    # PS2 console/pad buttons (not for PSX models)
    PS2_POWER = (_PS2_ADDRESS, 21)
    PS2_EJECT = (_PS2_ADDRESS, 22)
    PS2_RESET = (_PS2_ADDRESS, 23)
    PS2_POWER_ON = (_PS2_ADDRESS, 46)
    PS2_POWER_OFF = (_PS2_ADDRESS, 47)
    PS2_SELECT = (_PS2_ADDRESS, 80)
    PS2_L3 = (_PS2_ADDRESS, 81)
    PS2_R3 = (_PS2_ADDRESS, 82)
    PS2_START = (_PS2_ADDRESS, 83)
    PS2_UP = (_PS2_ADDRESS, 84)
    PS2_RIGHT = (_PS2_ADDRESS, 85)
    PS2_DOWN = (_PS2_ADDRESS, 86)
    PS2_LEFT = (_PS2_ADDRESS, 87)
    PS2_L2 = (_PS2_ADDRESS, 88)
    PS2_R2 = (_PS2_ADDRESS, 89)
    PS2_L1 = (_PS2_ADDRESS, 90)
    PS2_R1 = (_PS2_ADDRESS, 91)
    PS2_TRIANGLE = (_PS2_ADDRESS, 92)
    PS2_CIRCLE = (_PS2_ADDRESS, 93)
    PS2_CROSS = (_PS2_ADDRESS, 94)
    PS2_SQUARE = (_PS2_ADDRESS, 95)
    PS2_NO_LIGHT = (_PS2_ADDRESS, 117)

    def to_command(self) -> Command:
        """Build a SONY SIRC command for this PlayStation 2 code."""
        address, command = self.value

        return SonyCommand(
            address=address,
            address_bits=13,
            command=command,
        )


@dataclass(frozen=True, slots=True)
class PlayStation2Model:
    """A PlayStation 2 model and the IR codes it accepts."""

    name: str
    codes: frozenset[SonyPlayStation2Code]


# Common code sets reused across models.

_DVD_CODES = frozenset(
    {
        SonyPlayStation2Code.DVD_1,
        SonyPlayStation2Code.DVD_2,
        SonyPlayStation2Code.DVD_3,
        SonyPlayStation2Code.DVD_4,
        SonyPlayStation2Code.DVD_5,
        SonyPlayStation2Code.DVD_6,
        SonyPlayStation2Code.DVD_7,
        SonyPlayStation2Code.DVD_8,
        SonyPlayStation2Code.DVD_9,
        SonyPlayStation2Code.DVD_0,
        SonyPlayStation2Code.DVD_ENTER,
        SonyPlayStation2Code.DVD_RETURN,
        SonyPlayStation2Code.DVD_CLEAR,
        SonyPlayStation2Code.DVD_TITLE,
        SonyPlayStation2Code.DVD_MENU,
        SonyPlayStation2Code.DVD_PROGRAM,
        SonyPlayStation2Code.DVD_TIME,
        SonyPlayStation2Code.DVD_ATOB,
        SonyPlayStation2Code.DVD_REPEAT,
        SonyPlayStation2Code.DVD_PREV,
        SonyPlayStation2Code.DVD_NEXT,
        SonyPlayStation2Code.DVD_PLAY,
        SonyPlayStation2Code.DVD_SCAN_BACK,
        SonyPlayStation2Code.DVD_SCAN_FORW,
        SonyPlayStation2Code.DVD_SHUFFLE,
        SonyPlayStation2Code.DVD_STOP,
        SonyPlayStation2Code.DVD_PAUSE,
        SonyPlayStation2Code.DVD_DISPLAY,
        SonyPlayStation2Code.DVD_SLOW_BACK,
        SonyPlayStation2Code.DVD_SLOW_FORW,
        SonyPlayStation2Code.DVD_SUBTITLE,
        SonyPlayStation2Code.DVD_AUDIO,
        SonyPlayStation2Code.DVD_ANGLE,
        SonyPlayStation2Code.DVD_UP,
        SonyPlayStation2Code.DVD_DOWN,
        SonyPlayStation2Code.DVD_LEFT,
        SonyPlayStation2Code.DVD_RIGHT,
    }
)

_PS2_CODES = frozenset(
    {
        SonyPlayStation2Code.PS2_POWER,
        SonyPlayStation2Code.PS2_EJECT,
        SonyPlayStation2Code.PS2_RESET,
        SonyPlayStation2Code.PS2_POWER_ON,
        SonyPlayStation2Code.PS2_POWER_OFF,
        SonyPlayStation2Code.PS2_NO_LIGHT,
        SonyPlayStation2Code.PS2_SELECT,
        SonyPlayStation2Code.PS2_L3,
        SonyPlayStation2Code.PS2_R3,
        SonyPlayStation2Code.PS2_START,
        SonyPlayStation2Code.PS2_UP,
        SonyPlayStation2Code.PS2_RIGHT,
        SonyPlayStation2Code.PS2_DOWN,
        SonyPlayStation2Code.PS2_LEFT,
        SonyPlayStation2Code.PS2_L2,
        SonyPlayStation2Code.PS2_R2,
        SonyPlayStation2Code.PS2_L1,
        SonyPlayStation2Code.PS2_R1,
        SonyPlayStation2Code.PS2_TRIANGLE,
        SonyPlayStation2Code.PS2_CIRCLE,
        SonyPlayStation2Code.PS2_CROSS,
        SonyPlayStation2Code.PS2_SQUARE,
    }
)

PS2_FAT_WITHOUT_IR_MODELS = PlayStation2Model(
    name="PS2 Fat model without IR (SCPH-1X000 to SCPH-3X0XX, needs IR receiver)",
    codes=(_DVD_CODES | _PS2_CODES)
    - frozenset(
        {
            SonyPlayStation2Code.PS2_POWER,
            SonyPlayStation2Code.PS2_EJECT,
            SonyPlayStation2Code.PS2_RESET,
            SonyPlayStation2Code.PS2_POWER_ON,
            SonyPlayStation2Code.PS2_POWER_OFF,
            SonyPlayStation2Code.PS2_NO_LIGHT,
        }
    ),
)

PS2_FAT_WITH_IR_MODELS = PlayStation2Model(
    name="PS2 Fat model with IR (SCPH-5X00X)", codes=_DVD_CODES | _PS2_CODES
)

PS2_SLIM_MODELS = PlayStation2Model(
    name="PS2 Slim models (SCPH-7X0XX to SCPH-900XX)",
    codes=PS2_FAT_WITH_IR_MODELS.codes
    - frozenset(
        {
            SonyPlayStation2Code.PS2_EJECT,
        }
    ),
)

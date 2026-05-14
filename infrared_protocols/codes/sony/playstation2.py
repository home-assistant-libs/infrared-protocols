"""Command codes for Sony PlayStation 2 (SCPH-XXXXX) and PSX (DESR-XXXX).

Based on the following remote control models:
- SCPH-10150
- SCPH-10420
- RMT-P001
- RMT-P002J

Supported PS2 models:
- SCPH-1X000 to SCPH-3X0XX (needs SCPH-10160 IR receiver)
- SCPH-5X00X
- SCPH-7X0XX to SCPH-900XX (does not support Open/Close disc tray command)
- All PSX models (DESR-XXXX, not to be confused with PlayStation 1)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ...commands import Command
from ...commands.sony import SonyCommand

DVD_ADDRESS = 0x1A49
PS2_ADDRESS = 0x1ADA
PSX_ADDRESS_SWITCH_1 = 0x1A93
PSX_ADDRESS_SWITCH_2 = 0x1A9B
PSX_ADDRESS_SWITCH_3 = 0x1AA3
_PSX_ADDRESS_BY_SWITCH = {
    1: PSX_ADDRESS_SWITCH_1,
    2: PSX_ADDRESS_SWITCH_2,
    3: PSX_ADDRESS_SWITCH_3,
}


class SonyPlayStation2Code(Enum):
    """Sony PlayStation 2 IR command codes.

    All codes use 20-bit SONY SIRC (address_bits=13).

    DVD playback buttons share address 0x1A49 (device=26, subdevice=73).
    PS2 console/pad buttons share address 0x1ADA (device=26, subdevice=218).
    PSX buttons use one of three addresses depending on the remote switch:
    - switch 1: 0x1A93 (device=26, subdevice=147)
    - switch 2: 0x1A9B (device=26, subdevice=155)
    - switch 3: 0x1AA3 (device=26, subdevice=163)

    Values are (address, command) pairs.
    """

    # DVD playback buttons (not for PSX models)
    DVD_1 = (DVD_ADDRESS, 0)
    DVD_2 = (DVD_ADDRESS, 1)
    DVD_3 = (DVD_ADDRESS, 2)
    DVD_4 = (DVD_ADDRESS, 3)
    DVD_5 = (DVD_ADDRESS, 4)
    DVD_6 = (DVD_ADDRESS, 5)
    DVD_7 = (DVD_ADDRESS, 6)
    DVD_8 = (DVD_ADDRESS, 7)
    DVD_9 = (DVD_ADDRESS, 8)
    DVD_0 = (DVD_ADDRESS, 9)
    DVD_ENTER = (DVD_ADDRESS, 11)
    DVD_RETURN = (DVD_ADDRESS, 14)
    DVD_CLEAR = (DVD_ADDRESS, 15)
    DVD_TITLE = (DVD_ADDRESS, 26)
    DVD_MENU = (DVD_ADDRESS, 27)
    DVD_PROGRAM = (DVD_ADDRESS, 31)
    DVD_TIME = (DVD_ADDRESS, 40)
    DVD_ATOB = (DVD_ADDRESS, 42)
    DVD_REPEAT = (DVD_ADDRESS, 44)
    DVD_PREV = (DVD_ADDRESS, 48)
    DVD_NEXT = (DVD_ADDRESS, 49)
    DVD_PLAY = (DVD_ADDRESS, 50)
    DVD_SCAN_BACK = (DVD_ADDRESS, 51)
    DVD_SCAN_FORW = (DVD_ADDRESS, 52)
    DVD_SHUFFLE = (DVD_ADDRESS, 53)
    DVD_STOP = (DVD_ADDRESS, 56)
    DVD_PAUSE = (DVD_ADDRESS, 57)
    DVD_DISPLAY = (DVD_ADDRESS, 84)
    DVD_SLOW_BACK = (DVD_ADDRESS, 96)
    DVD_SLOW_FORW = (DVD_ADDRESS, 97)
    DVD_SUBTITLE = (DVD_ADDRESS, 99)
    DVD_AUDIO = (DVD_ADDRESS, 100)
    DVD_ANGLE = (DVD_ADDRESS, 101)
    DVD_UP = (DVD_ADDRESS, 121)
    DVD_DOWN = (DVD_ADDRESS, 122)
    DVD_LEFT = (DVD_ADDRESS, 123)
    DVD_RIGHT = (DVD_ADDRESS, 124)

    # PS2 console/pad buttons (not for PSX models)
    PS2_POWER = (PS2_ADDRESS, 21)
    PS2_EJECT = (PS2_ADDRESS, 22)
    PS2_RESET = (PS2_ADDRESS, 23)
    PS2_POWER_ON = (PS2_ADDRESS, 46)
    PS2_POWER_OFF = (PS2_ADDRESS, 47)
    PS2_SELECT = (PS2_ADDRESS, 80)
    PS2_L3 = (PS2_ADDRESS, 81)
    PS2_R3 = (PS2_ADDRESS, 82)
    PS2_START = (PS2_ADDRESS, 83)
    PS2_UP = (PS2_ADDRESS, 84)
    PS2_RIGHT = (PS2_ADDRESS, 85)
    PS2_DOWN = (PS2_ADDRESS, 86)
    PS2_LEFT = (PS2_ADDRESS, 87)
    PS2_L2 = (PS2_ADDRESS, 88)
    PS2_R2 = (PS2_ADDRESS, 89)
    PS2_L1 = (PS2_ADDRESS, 90)
    PS2_R1 = (PS2_ADDRESS, 91)
    PS2_TRIANGLE = (PS2_ADDRESS, 92)
    PS2_CIRCLE = (PS2_ADDRESS, 93)
    PS2_CROSS = (PS2_ADDRESS, 94)
    PS2_SQUARE = (PS2_ADDRESS, 95)
    PS2_NO_LIGHT = (PS2_ADDRESS, 117)

    # PSX buttons (not for PS2 models)
    # - These use the switch-1 address by default; use ``psx_switch`` in
    #   ``to_command`` to send the same command on switch 2/3 addresses.
    # - Since analog broadcasting ended on July 24, 2011, some commands are no
    #   longer relevant.
    DESR_1 = (PSX_ADDRESS_SWITCH_1, 0)
    DESR_2 = (PSX_ADDRESS_SWITCH_1, 1)
    DESR_3 = (PSX_ADDRESS_SWITCH_1, 2)
    DESR_4 = (PSX_ADDRESS_SWITCH_1, 3)
    DESR_5 = (PSX_ADDRESS_SWITCH_1, 4)
    DESR_6 = (PSX_ADDRESS_SWITCH_1, 5)
    DESR_7 = (PSX_ADDRESS_SWITCH_1, 6)
    DESR_8 = (PSX_ADDRESS_SWITCH_1, 7)
    DESR_9 = (PSX_ADDRESS_SWITCH_1, 8)
    DESR_10 = (PSX_ADDRESS_SWITCH_1, 9)
    DESR_11 = (PSX_ADDRESS_SWITCH_1, 10)
    DESR_12 = (PSX_ADDRESS_SWITCH_1, 11)
    DESR_BS_7 = (PSX_ADDRESS_SWITCH_1, 13)  # Only for RMT-P001
    DESR_BS_11 = (PSX_ADDRESS_SWITCH_1, 14)  # Only for RMT-P001
    DESR_CLEAR = (PSX_ADDRESS_SWITCH_1, 15)
    DESR_POWER = (PSX_ADDRESS_SWITCH_1, 21)
    DESR_EJECT = (PSX_ADDRESS_SWITCH_1, 22)
    DESR_STOP = (PSX_ADDRESS_SWITCH_1, 24)
    DESR_PAUSE = (PSX_ADDRESS_SWITCH_1, 25)
    DESR_PLAY = (PSX_ADDRESS_SWITCH_1, 26)
    DESR_RECORD_START = (PSX_ADDRESS_SWITCH_1, 29)
    DESR_RECORD_PAUSE = (PSX_ADDRESS_SWITCH_1, 30)
    DESR_RECORD_STOP = (PSX_ADDRESS_SWITCH_1, 31)
    DESR_DISPLAY = (PSX_ADDRESS_SWITCH_1, 37)
    DESR_RECORDING_MODE = (PSX_ADDRESS_SWITCH_1, 38)
    DESR_MENU = (PSX_ADDRESS_SWITCH_1, 41)
    DESR_PROGRAM = (PSX_ADDRESS_SWITCH_1, 42)
    DESR_TOP_MENU = (PSX_ADDRESS_SWITCH_1, 44)
    DESR_G_GUIDE2 = (PSX_ADDRESS_SWITCH_1, 65)  # Only for RMT-P002J
    DESR_HOME = (PSX_ADDRESS_SWITCH_1, 66)
    DESR_RETURN = (PSX_ADDRESS_SWITCH_1, 67)
    DESR_G_GUIDE = (PSX_ADDRESS_SWITCH_1, 69)  # Only for RMT-P001
    DESR_SELECT = (PSX_ADDRESS_SWITCH_1, 80)
    DESR_L3 = (PSX_ADDRESS_SWITCH_1, 81)
    DESR_R3 = (PSX_ADDRESS_SWITCH_1, 82)
    DESR_START = (PSX_ADDRESS_SWITCH_1, 83)
    DESR_UP = (PSX_ADDRESS_SWITCH_1, 84)
    DESR_RIGHT = (PSX_ADDRESS_SWITCH_1, 85)
    DESR_DOWN = (PSX_ADDRESS_SWITCH_1, 86)
    DESR_LEFT = (PSX_ADDRESS_SWITCH_1, 87)
    DESR_L2_SCAN_BACK = (PSX_ADDRESS_SWITCH_1, 88)
    DESR_R2_SCAN_FORW = (PSX_ADDRESS_SWITCH_1, 89)
    DESR_L1_PREV = (PSX_ADDRESS_SWITCH_1, 90)
    DESR_R1_NEXT = (PSX_ADDRESS_SWITCH_1, 91)
    DESR_TRIANGLE_OPTION = (PSX_ADDRESS_SWITCH_1, 92)
    DESR_CIRCLE = (PSX_ADDRESS_SWITCH_1, 93)
    DESR_CROSS_BACK = (PSX_ADDRESS_SWITCH_1, 94)
    DESR_SQUARE_VIEW = (PSX_ADDRESS_SWITCH_1, 95)
    DESR_ENTER = (PSX_ADDRESS_SWITCH_1, 96)
    DESR_QUIT_GAME = (PSX_ADDRESS_SWITCH_1, 97)
    DESR_DELETE = (PSX_ADDRESS_SWITCH_1, 98)
    DESR_FLASH_FORW = (PSX_ADDRESS_SWITCH_1, 117)  # Only for RMT-P002J
    DESR_FLASH_BACK = (PSX_ADDRESS_SWITCH_1, 118)  # Only for RMT-P002J

    def to_command(self, *, psx_switch: int = 1) -> Command:
        """Build a SONY SIRC command for this PlayStation 2/PSX code.

        For DESR codes, set ``psx_switch`` to 1, 2, or 3 to select the
        corresponding PSX remote switch position address.
        """
        if psx_switch not in _PSX_ADDRESS_BY_SWITCH:
            raise ValueError("psx_switch must be one of 1, 2, or 3")

        address, command = self.value
        if self.name.startswith("DESR_"):
            address = _PSX_ADDRESS_BY_SWITCH[psx_switch]

        return SonyCommand(
            address=address,
            address_bits=13,
            command=command,
        )


@dataclass(frozen=True, slots=True)
class PlayStation2Model:
    """A PlayStation 2 / PSX model and the IR codes it accepts."""

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

_DESR_COMMON_CODES = frozenset(
    {
        SonyPlayStation2Code.DESR_EJECT,
        SonyPlayStation2Code.DESR_QUIT_GAME,
        SonyPlayStation2Code.DESR_POWER,
        SonyPlayStation2Code.DESR_1,
        SonyPlayStation2Code.DESR_2,
        SonyPlayStation2Code.DESR_3,
        SonyPlayStation2Code.DESR_4,
        SonyPlayStation2Code.DESR_5,
        SonyPlayStation2Code.DESR_6,
        SonyPlayStation2Code.DESR_7,
        SonyPlayStation2Code.DESR_8,
        SonyPlayStation2Code.DESR_9,
        SonyPlayStation2Code.DESR_10,
        SonyPlayStation2Code.DESR_11,
        SonyPlayStation2Code.DESR_12,
        SonyPlayStation2Code.DESR_CLEAR,
        SonyPlayStation2Code.DESR_TOP_MENU,
        SonyPlayStation2Code.DESR_MENU,
        SonyPlayStation2Code.DESR_RETURN,
        SonyPlayStation2Code.DESR_TRIANGLE_OPTION,
        SonyPlayStation2Code.DESR_CIRCLE,
        SonyPlayStation2Code.DESR_SQUARE_VIEW,
        SonyPlayStation2Code.DESR_CROSS_BACK,
        SonyPlayStation2Code.DESR_UP,
        SonyPlayStation2Code.DESR_LEFT,
        SonyPlayStation2Code.DESR_RIGHT,
        SonyPlayStation2Code.DESR_DOWN,
        SonyPlayStation2Code.DESR_ENTER,
        SonyPlayStation2Code.DESR_PROGRAM,
        SonyPlayStation2Code.DESR_HOME,
        SonyPlayStation2Code.DESR_DISPLAY,
        SonyPlayStation2Code.DESR_L1_PREV,
        SonyPlayStation2Code.DESR_L3,
        SonyPlayStation2Code.DESR_R3,
        SonyPlayStation2Code.DESR_R1_NEXT,
        SonyPlayStation2Code.DESR_L2_SCAN_BACK,
        SonyPlayStation2Code.DESR_SELECT,
        SonyPlayStation2Code.DESR_START,
        SonyPlayStation2Code.DESR_R2_SCAN_FORW,
        SonyPlayStation2Code.DESR_PLAY,
        SonyPlayStation2Code.DESR_PAUSE,
        SonyPlayStation2Code.DESR_STOP,
        SonyPlayStation2Code.DESR_RECORDING_MODE,
        SonyPlayStation2Code.DESR_RECORD_START,
        SonyPlayStation2Code.DESR_RECORD_PAUSE,
        SonyPlayStation2Code.DESR_RECORD_STOP,
        SonyPlayStation2Code.DESR_DELETE,
    }
)

_DESR_P001_ONLY_CODES = frozenset(
    {
        SonyPlayStation2Code.DESR_G_GUIDE,
        SonyPlayStation2Code.DESR_BS_7,
        SonyPlayStation2Code.DESR_BS_11,
    }
)

_DESR_P002J_ONLY_CODES = frozenset(
    {
        SonyPlayStation2Code.DESR_G_GUIDE2,
        SonyPlayStation2Code.DESR_FLASH_BACK,
        SonyPlayStation2Code.DESR_FLASH_FORW,
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
    name="PS2 Fat model with IR (SCPH-5X00X)",
    codes=_DVD_CODES | _PS2_CODES
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

PSX_EARLIER_MODELS = PlayStation2Model(
    name="PSX earlier models (DESR-5000, DESR-7000, DESR-5100, and DESR-7100)",
    codes=_DESR_COMMON_CODES | _DESR_P001_ONLY_CODES,
)

PSX_LATER_MODELS = PlayStation2Model(
    name="PSX later models (DESR-5500, DESR-7500, DESR-5700, and DESR-7700)",
    codes=_DESR_COMMON_CODES | _DESR_P002J_ONLY_CODES,
)


#: All known PlayStation 2 / PSX model groups, for iteration.
ALL_MODELS: tuple[PlayStation2Model, ...] = (
    PS2_FAT_WITHOUT_IR_MODELS,
    PS2_FAT_WITH_IR_MODELS,
    PS2_SLIM_MODELS,
    PSX_EARLIER_MODELS,
    PSX_LATER_MODELS,
)

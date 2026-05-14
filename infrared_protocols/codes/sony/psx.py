"""Command codes for Sony PSX (DESR-XXXX).

Based on the following remote control models:
- RMT-P001 (bundled with earlier PSX models)
- RMT-P002J (bundled with later PSX models)

Supported PSX models:
- DESR-5000, DESR-7000, DESR-5100, DESR-7100 (earlier models)
- DESR-5500, DESR-7500, DESR-5700, DESR-7700 (later models)

The PSX remote receiver unit has a switch that selects the IR address.
Three switch positions (1, 2, 3) map to three distinct addresses, allowing
multiple PSX units to be controlled independently in the same room.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ...commands import Command
from ...commands.sony import SonyCommand

_ADDRESS_SWITCH_1 = 0x1A93
_ADDRESS_SWITCH_2 = 0x1A9B
_ADDRESS_SWITCH_3 = 0x1AA3

# region Command code values
_CMD_1 = 0
_CMD_2 = 1
_CMD_3 = 2
_CMD_4 = 3
_CMD_5 = 4
_CMD_6 = 5
_CMD_7 = 6
_CMD_8 = 7
_CMD_9 = 8
_CMD_10 = 9
_CMD_11 = 10
_CMD_12 = 11
_CMD_BS_7 = 13  # RMT-P001 only
_CMD_BS_11 = 14  # RMT-P001 only
_CMD_CLEAR = 15
_CMD_POWER = 21
_CMD_EJECT = 22
_CMD_STOP = 24
_CMD_PAUSE = 25
_CMD_PLAY = 26
_CMD_RECORD_START = 29
_CMD_RECORD_PAUSE = 30
_CMD_RECORD_STOP = 31
_CMD_DISPLAY = 37
_CMD_RECORDING_MODE = 38
_CMD_MENU = 41
_CMD_PROGRAM = 42
_CMD_TOP_MENU = 44
_CMD_G_GUIDE2 = 65  # RMT-P002J only
_CMD_HOME = 66
_CMD_RETURN = 67
_CMD_G_GUIDE = 69  # RMT-P001 only
_CMD_SELECT = 80
_CMD_L3 = 81
_CMD_R3 = 82
_CMD_START = 83
_CMD_UP = 84
_CMD_RIGHT = 85
_CMD_DOWN = 86
_CMD_LEFT = 87
_CMD_L2_SCAN_BACK = 88
_CMD_R2_SCAN_FORW = 89
_CMD_L1_PREV = 90
_CMD_R1_NEXT = 91
_CMD_TRIANGLE_OPTION = 92
_CMD_CIRCLE = 93
_CMD_CROSS_BACK = 94
_CMD_SQUARE_VIEW = 95
_CMD_ENTER = 96
_CMD_QUIT_GAME = 97
_CMD_DELETE = 98
_CMD_FLASH_FORW = 117  # RMT-P002J only
_CMD_FLASH_BACK = 118  # RMT-P002J only
# endregion Command code values

# Code grouping by remote model
_P001_ONLY_COMMANDS = frozenset(
    [
        _CMD_G_GUIDE,
        _CMD_BS_7,
        _CMD_BS_11,
    ]
)

_P002J_ONLY_COMMANDS = frozenset(
    [
        _CMD_G_GUIDE2,
        _CMD_FLASH_FORW,
        _CMD_FLASH_BACK,
    ]
)


class _PSXSwitchCodeMixin:
    """Non-Enum mixin providing to_command() for PSX DIP-switch code enums.

    Values in the concrete Enum subclasses are (address, command) pairs.
    """

    def to_command(self) -> Command:
        """Build a SONY SIRC command for this PSX code."""
        address, command = self.value  # type: ignore[attr-defined]
        return SonyCommand(
            address=address,
            address_bits=13,
            command=command,
        )


class SonyPSXSwitch1Code(_PSXSwitchCodeMixin, Enum):
    """Sony PSX (remote switch 1) IR command codes.

    All codes use 20-bit SONY SIRC (address_bits=13).

    address is 0x1A93 for switch position 1.

    Values are (address, command) pairs.
    """

    NUM_1 = (_ADDRESS_SWITCH_1, _CMD_1)
    NUM_2 = (_ADDRESS_SWITCH_1, _CMD_2)
    NUM_3 = (_ADDRESS_SWITCH_1, _CMD_3)
    NUM_4 = (_ADDRESS_SWITCH_1, _CMD_4)
    NUM_5 = (_ADDRESS_SWITCH_1, _CMD_5)
    NUM_6 = (_ADDRESS_SWITCH_1, _CMD_6)
    NUM_7 = (_ADDRESS_SWITCH_1, _CMD_7)
    NUM_8 = (_ADDRESS_SWITCH_1, _CMD_8)
    NUM_9 = (_ADDRESS_SWITCH_1, _CMD_9)
    NUM_10 = (_ADDRESS_SWITCH_1, _CMD_10)
    NUM_11 = (_ADDRESS_SWITCH_1, _CMD_11)
    NUM_12 = (_ADDRESS_SWITCH_1, _CMD_12)
    BS_7 = (_ADDRESS_SWITCH_1, _CMD_BS_7)
    BS_11 = (_ADDRESS_SWITCH_1, _CMD_BS_11)
    CLEAR = (_ADDRESS_SWITCH_1, _CMD_CLEAR)
    POWER = (_ADDRESS_SWITCH_1, _CMD_POWER)
    EJECT = (_ADDRESS_SWITCH_1, _CMD_EJECT)
    STOP = (_ADDRESS_SWITCH_1, _CMD_STOP)
    PAUSE = (_ADDRESS_SWITCH_1, _CMD_PAUSE)
    PLAY = (_ADDRESS_SWITCH_1, _CMD_PLAY)
    RECORD_START = (_ADDRESS_SWITCH_1, _CMD_RECORD_START)
    RECORD_PAUSE = (_ADDRESS_SWITCH_1, _CMD_RECORD_PAUSE)
    RECORD_STOP = (_ADDRESS_SWITCH_1, _CMD_RECORD_STOP)
    DISPLAY = (_ADDRESS_SWITCH_1, _CMD_DISPLAY)
    RECORDING_MODE = (_ADDRESS_SWITCH_1, _CMD_RECORDING_MODE)
    MENU = (_ADDRESS_SWITCH_1, _CMD_MENU)
    PROGRAM = (_ADDRESS_SWITCH_1, _CMD_PROGRAM)
    TOP_MENU = (_ADDRESS_SWITCH_1, _CMD_TOP_MENU)
    G_GUIDE2 = (_ADDRESS_SWITCH_1, _CMD_G_GUIDE2)
    HOME = (_ADDRESS_SWITCH_1, _CMD_HOME)
    RETURN = (_ADDRESS_SWITCH_1, _CMD_RETURN)
    G_GUIDE = (_ADDRESS_SWITCH_1, _CMD_G_GUIDE)
    SELECT = (_ADDRESS_SWITCH_1, _CMD_SELECT)
    L3 = (_ADDRESS_SWITCH_1, _CMD_L3)
    R3 = (_ADDRESS_SWITCH_1, _CMD_R3)
    START = (_ADDRESS_SWITCH_1, _CMD_START)
    UP = (_ADDRESS_SWITCH_1, _CMD_UP)
    RIGHT = (_ADDRESS_SWITCH_1, _CMD_RIGHT)
    DOWN = (_ADDRESS_SWITCH_1, _CMD_DOWN)
    LEFT = (_ADDRESS_SWITCH_1, _CMD_LEFT)
    L2_SCAN_BACK = (_ADDRESS_SWITCH_1, _CMD_L2_SCAN_BACK)
    R2_SCAN_FORW = (_ADDRESS_SWITCH_1, _CMD_R2_SCAN_FORW)
    L1_PREV = (_ADDRESS_SWITCH_1, _CMD_L1_PREV)
    R1_NEXT = (_ADDRESS_SWITCH_1, _CMD_R1_NEXT)
    TRIANGLE_OPTION = (_ADDRESS_SWITCH_1, _CMD_TRIANGLE_OPTION)
    CIRCLE = (_ADDRESS_SWITCH_1, _CMD_CIRCLE)
    CROSS_BACK = (_ADDRESS_SWITCH_1, _CMD_CROSS_BACK)
    SQUARE_VIEW = (_ADDRESS_SWITCH_1, _CMD_SQUARE_VIEW)
    ENTER = (_ADDRESS_SWITCH_1, _CMD_ENTER)
    QUIT_GAME = (_ADDRESS_SWITCH_1, _CMD_QUIT_GAME)
    DELETE = (_ADDRESS_SWITCH_1, _CMD_DELETE)
    FLASH_FORW = (_ADDRESS_SWITCH_1, _CMD_FLASH_FORW)
    FLASH_BACK = (_ADDRESS_SWITCH_1, _CMD_FLASH_BACK)


class SonyPSXSwitch2Code(_PSXSwitchCodeMixin, Enum):
    """Sony PSX (remote switch 2) IR command codes.

    All codes use 20-bit SONY SIRC (address_bits=13).

    address is 0x1A9B for switch position 2.

    Values are (address, command) pairs.
    """

    NUM_1 = (_ADDRESS_SWITCH_2, _CMD_1)
    NUM_2 = (_ADDRESS_SWITCH_2, _CMD_2)
    NUM_3 = (_ADDRESS_SWITCH_2, _CMD_3)
    NUM_4 = (_ADDRESS_SWITCH_2, _CMD_4)
    NUM_5 = (_ADDRESS_SWITCH_2, _CMD_5)
    NUM_6 = (_ADDRESS_SWITCH_2, _CMD_6)
    NUM_7 = (_ADDRESS_SWITCH_2, _CMD_7)
    NUM_8 = (_ADDRESS_SWITCH_2, _CMD_8)
    NUM_9 = (_ADDRESS_SWITCH_2, _CMD_9)
    NUM_10 = (_ADDRESS_SWITCH_2, _CMD_10)
    NUM_11 = (_ADDRESS_SWITCH_2, _CMD_11)
    NUM_12 = (_ADDRESS_SWITCH_2, _CMD_12)
    BS_7 = (_ADDRESS_SWITCH_2, _CMD_BS_7)
    BS_11 = (_ADDRESS_SWITCH_2, _CMD_BS_11)
    CLEAR = (_ADDRESS_SWITCH_2, _CMD_CLEAR)
    POWER = (_ADDRESS_SWITCH_2, _CMD_POWER)
    EJECT = (_ADDRESS_SWITCH_2, _CMD_EJECT)
    STOP = (_ADDRESS_SWITCH_2, _CMD_STOP)
    PAUSE = (_ADDRESS_SWITCH_2, _CMD_PAUSE)
    PLAY = (_ADDRESS_SWITCH_2, _CMD_PLAY)
    RECORD_START = (_ADDRESS_SWITCH_2, _CMD_RECORD_START)
    RECORD_PAUSE = (_ADDRESS_SWITCH_2, _CMD_RECORD_PAUSE)
    RECORD_STOP = (_ADDRESS_SWITCH_2, _CMD_RECORD_STOP)
    DISPLAY = (_ADDRESS_SWITCH_2, _CMD_DISPLAY)
    RECORDING_MODE = (_ADDRESS_SWITCH_2, _CMD_RECORDING_MODE)
    MENU = (_ADDRESS_SWITCH_2, _CMD_MENU)
    PROGRAM = (_ADDRESS_SWITCH_2, _CMD_PROGRAM)
    TOP_MENU = (_ADDRESS_SWITCH_2, _CMD_TOP_MENU)
    G_GUIDE2 = (_ADDRESS_SWITCH_2, _CMD_G_GUIDE2)
    HOME = (_ADDRESS_SWITCH_2, _CMD_HOME)
    RETURN = (_ADDRESS_SWITCH_2, _CMD_RETURN)
    G_GUIDE = (_ADDRESS_SWITCH_2, _CMD_G_GUIDE)
    SELECT = (_ADDRESS_SWITCH_2, _CMD_SELECT)
    L3 = (_ADDRESS_SWITCH_2, _CMD_L3)
    R3 = (_ADDRESS_SWITCH_2, _CMD_R3)
    START = (_ADDRESS_SWITCH_2, _CMD_START)
    UP = (_ADDRESS_SWITCH_2, _CMD_UP)
    RIGHT = (_ADDRESS_SWITCH_2, _CMD_RIGHT)
    DOWN = (_ADDRESS_SWITCH_2, _CMD_DOWN)
    LEFT = (_ADDRESS_SWITCH_2, _CMD_LEFT)
    L2_SCAN_BACK = (_ADDRESS_SWITCH_2, _CMD_L2_SCAN_BACK)
    R2_SCAN_FORW = (_ADDRESS_SWITCH_2, _CMD_R2_SCAN_FORW)
    L1_PREV = (_ADDRESS_SWITCH_2, _CMD_L1_PREV)
    R1_NEXT = (_ADDRESS_SWITCH_2, _CMD_R1_NEXT)
    TRIANGLE_OPTION = (_ADDRESS_SWITCH_2, _CMD_TRIANGLE_OPTION)
    CIRCLE = (_ADDRESS_SWITCH_2, _CMD_CIRCLE)
    CROSS_BACK = (_ADDRESS_SWITCH_2, _CMD_CROSS_BACK)
    SQUARE_VIEW = (_ADDRESS_SWITCH_2, _CMD_SQUARE_VIEW)
    ENTER = (_ADDRESS_SWITCH_2, _CMD_ENTER)
    QUIT_GAME = (_ADDRESS_SWITCH_2, _CMD_QUIT_GAME)
    DELETE = (_ADDRESS_SWITCH_2, _CMD_DELETE)
    FLASH_FORW = (_ADDRESS_SWITCH_2, _CMD_FLASH_FORW)
    FLASH_BACK = (_ADDRESS_SWITCH_2, _CMD_FLASH_BACK)


class SonyPSXSwitch3Code(_PSXSwitchCodeMixin, Enum):
    """Sony PSX (remote switch 3) IR command codes.

    All codes use 20-bit SONY SIRC (address_bits=13).

    address is 0x1AA3 for switch position 3.

    Values are (address, command) pairs.
    """

    NUM_1 = (_ADDRESS_SWITCH_3, _CMD_1)
    NUM_2 = (_ADDRESS_SWITCH_3, _CMD_2)
    NUM_3 = (_ADDRESS_SWITCH_3, _CMD_3)
    NUM_4 = (_ADDRESS_SWITCH_3, _CMD_4)
    NUM_5 = (_ADDRESS_SWITCH_3, _CMD_5)
    NUM_6 = (_ADDRESS_SWITCH_3, _CMD_6)
    NUM_7 = (_ADDRESS_SWITCH_3, _CMD_7)
    NUM_8 = (_ADDRESS_SWITCH_3, _CMD_8)
    NUM_9 = (_ADDRESS_SWITCH_3, _CMD_9)
    NUM_10 = (_ADDRESS_SWITCH_3, _CMD_10)
    NUM_11 = (_ADDRESS_SWITCH_3, _CMD_11)
    NUM_12 = (_ADDRESS_SWITCH_3, _CMD_12)
    BS_7 = (_ADDRESS_SWITCH_3, _CMD_BS_7)
    BS_11 = (_ADDRESS_SWITCH_3, _CMD_BS_11)
    CLEAR = (_ADDRESS_SWITCH_3, _CMD_CLEAR)
    POWER = (_ADDRESS_SWITCH_3, _CMD_POWER)
    EJECT = (_ADDRESS_SWITCH_3, _CMD_EJECT)
    STOP = (_ADDRESS_SWITCH_3, _CMD_STOP)
    PAUSE = (_ADDRESS_SWITCH_3, _CMD_PAUSE)
    PLAY = (_ADDRESS_SWITCH_3, _CMD_PLAY)
    RECORD_START = (_ADDRESS_SWITCH_3, _CMD_RECORD_START)
    RECORD_PAUSE = (_ADDRESS_SWITCH_3, _CMD_RECORD_PAUSE)
    RECORD_STOP = (_ADDRESS_SWITCH_3, _CMD_RECORD_STOP)
    DISPLAY = (_ADDRESS_SWITCH_3, _CMD_DISPLAY)
    RECORDING_MODE = (_ADDRESS_SWITCH_3, _CMD_RECORDING_MODE)
    MENU = (_ADDRESS_SWITCH_3, _CMD_MENU)
    PROGRAM = (_ADDRESS_SWITCH_3, _CMD_PROGRAM)
    TOP_MENU = (_ADDRESS_SWITCH_3, _CMD_TOP_MENU)
    G_GUIDE2 = (_ADDRESS_SWITCH_3, _CMD_G_GUIDE2)
    HOME = (_ADDRESS_SWITCH_3, _CMD_HOME)
    RETURN = (_ADDRESS_SWITCH_3, _CMD_RETURN)
    G_GUIDE = (_ADDRESS_SWITCH_3, _CMD_G_GUIDE)
    SELECT = (_ADDRESS_SWITCH_3, _CMD_SELECT)
    L3 = (_ADDRESS_SWITCH_3, _CMD_L3)
    R3 = (_ADDRESS_SWITCH_3, _CMD_R3)
    START = (_ADDRESS_SWITCH_3, _CMD_START)
    UP = (_ADDRESS_SWITCH_3, _CMD_UP)
    RIGHT = (_ADDRESS_SWITCH_3, _CMD_RIGHT)
    DOWN = (_ADDRESS_SWITCH_3, _CMD_DOWN)
    LEFT = (_ADDRESS_SWITCH_3, _CMD_LEFT)
    L2_SCAN_BACK = (_ADDRESS_SWITCH_3, _CMD_L2_SCAN_BACK)
    R2_SCAN_FORW = (_ADDRESS_SWITCH_3, _CMD_R2_SCAN_FORW)
    L1_PREV = (_ADDRESS_SWITCH_3, _CMD_L1_PREV)
    R1_NEXT = (_ADDRESS_SWITCH_3, _CMD_R1_NEXT)
    TRIANGLE_OPTION = (_ADDRESS_SWITCH_3, _CMD_TRIANGLE_OPTION)
    CIRCLE = (_ADDRESS_SWITCH_3, _CMD_CIRCLE)
    CROSS_BACK = (_ADDRESS_SWITCH_3, _CMD_CROSS_BACK)
    SQUARE_VIEW = (_ADDRESS_SWITCH_3, _CMD_SQUARE_VIEW)
    ENTER = (_ADDRESS_SWITCH_3, _CMD_ENTER)
    QUIT_GAME = (_ADDRESS_SWITCH_3, _CMD_QUIT_GAME)
    DELETE = (_ADDRESS_SWITCH_3, _CMD_DELETE)
    FLASH_FORW = (_ADDRESS_SWITCH_3, _CMD_FLASH_FORW)
    FLASH_BACK = (_ADDRESS_SWITCH_3, _CMD_FLASH_BACK)


@dataclass(frozen=True, slots=True)
class PSXModel:
    """A Sony PSX model and the IR codes it accepts for a specific switch setting."""

    name: str
    codes: frozenset[Enum]


# Model variants: earlier (RMT-P001) and later (RMT-P002J) PSX models.
# Each grouped by switch position.
# Earlier models include only common codes and P001-exclusive codes.
# Later models include common codes and P002J-exclusive codes.
PSX_EARLIER_MODELS_SWITCH_1 = PSXModel(
    name=(
        "PSX earlier models (DESR-5000, DESR-7000, DESR-5100, and DESR-7100), switch 1"
    ),
    codes=frozenset(
        code
        for code in SonyPSXSwitch1Code
        if code.value[1] not in (_P002J_ONLY_COMMANDS)
    ),
)

PSX_EARLIER_MODELS_SWITCH_2 = PSXModel(
    name=(
        "PSX earlier models (DESR-5000, DESR-7000, DESR-5100, and DESR-7100), switch 2"
    ),
    codes=frozenset(
        code
        for code in SonyPSXSwitch2Code
        if code.value[1] not in (_P002J_ONLY_COMMANDS)
    ),
)

PSX_EARLIER_MODELS_SWITCH_3 = PSXModel(
    name=(
        "PSX earlier models (DESR-5000, DESR-7000, DESR-5100, and DESR-7100), switch 3"
    ),
    codes=frozenset(
        code
        for code in SonyPSXSwitch3Code
        if code.value[1] not in (_P002J_ONLY_COMMANDS)
    ),
)

PSX_LATER_MODELS_SWITCH_1 = PSXModel(
    name=(
        "PSX later models (DESR-5500, DESR-7500, DESR-5700, and DESR-7700), switch 1"
    ),
    codes=frozenset(
        code
        for code in SonyPSXSwitch1Code
        if code.value[1] not in (_P001_ONLY_COMMANDS)
    ),
)

PSX_LATER_MODELS_SWITCH_2 = PSXModel(
    name=(
        "PSX later models (DESR-5500, DESR-7500, DESR-5700, and DESR-7700), switch 2"
    ),
    codes=frozenset(
        code
        for code in SonyPSXSwitch2Code
        if code.value[1] not in (_P001_ONLY_COMMANDS)
    ),
)

PSX_LATER_MODELS_SWITCH_3 = PSXModel(
    name=(
        "PSX later models (DESR-5500, DESR-7500, DESR-5700, and DESR-7700), switch 3"
    ),
    codes=frozenset(
        code
        for code in SonyPSXSwitch3Code
        if code.value[1] not in (_P001_ONLY_COMMANDS)
    ),
)

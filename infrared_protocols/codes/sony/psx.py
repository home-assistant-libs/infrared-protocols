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

_SWITCH_TO_ADDRESS = {
    1: 0x1A93,
    2: 0x1A9B,
    3: 0x1AA3,
}


class SonyPSXCode(Enum):
    """Sony PSX IR command codes.

    All codes use 20-bit SONY SIRC (address_bits=13).

    address:
    - 0x1A93: switch position 1
    - 0x1A9B: switch position 2
    - 0x1AA3: switch position 3
    """

    NUM_1 = 0
    NUM_2 = 1
    NUM_3 = 2
    NUM_4 = 3
    NUM_5 = 4
    NUM_6 = 5
    NUM_7 = 6
    NUM_8 = 7
    NUM_9 = 8
    NUM_10 = 9
    NUM_11 = 10
    NUM_12 = 11
    BS_7 = 13  # RMT-P001 only
    BS_11 = 14  # RMT-P001 only
    CLEAR = 15
    POWER = 21
    EJECT = 22
    STOP = 24
    PAUSE = 25
    PLAY = 26
    RECORD_START = 29
    RECORD_PAUSE = 30
    RECORD_STOP = 31
    DISPLAY = 37
    RECORDING_MODE = 38
    MENU = 41
    PROGRAM = 42
    TOP_MENU = 44
    G_GUIDE2 = 65  # RMT-P002J only
    HOME = 66
    RETURN = 67
    G_GUIDE = 69  # RMT-P001 only
    SELECT = 80
    L3 = 81
    R3 = 82
    START = 83
    UP = 84
    RIGHT = 85
    DOWN = 86
    LEFT = 87
    L2_SCAN_BACK = 88
    R2_SCAN_FORW = 89
    L1_PREV = 90
    R1_NEXT = 91
    TRIANGLE_OPTION = 92
    CIRCLE = 93
    CROSS_BACK = 94
    SQUARE_VIEW = 95
    ENTER = 96
    QUIT_GAME = 97
    DELETE = 98
    FLASH_FORW = 117  # RMT-P002J only
    FLASH_BACK = 118  # RMT-P002J only

    def to_command(self, switch: int = 1) -> Command:
        """Build a SONY SIRC command for this PSX code.

        :param switch: The switch position on the PSX remote receiver unit (1, 2, or 3).
            Each position maps to a distinct IR address, allowing multiple PSX units
            to be controlled independently in the same room. Defaults to 1.
        """
        if switch not in _SWITCH_TO_ADDRESS:
            raise ValueError(f"Invalid switch position: {switch}")

        command = self.value
        return SonyCommand(
            address=_SWITCH_TO_ADDRESS[switch],
            address_bits=13,
            command=command,
        )


@dataclass(frozen=True, slots=True)
class PSXModel:
    """A Sony PSX model and the IR codes it accepts for a specific switch setting."""

    name: str
    codes: frozenset[SonyPSXCode]


# Code grouping by remote model
_P001_ONLY_COMMANDS = frozenset(
    [
        SonyPSXCode.BS_7,
        SonyPSXCode.BS_11,
        SonyPSXCode.G_GUIDE,
    ]
)

_P002J_ONLY_COMMANDS = frozenset(
    [
        SonyPSXCode.G_GUIDE2,
        SonyPSXCode.FLASH_FORW,
        SonyPSXCode.FLASH_BACK,
    ]
)

# Model variants: earlier (RMT-P001) and later (RMT-P002J) PSX models.
# Earlier models include only common codes and P001-exclusive codes.
# Later models include common codes and P002J-exclusive codes.
PSX_EARLIER_MODELS = PSXModel(
    name=("PSX earlier models (DESR-5000, DESR-7000, DESR-5100, and DESR-7100)"),
    codes=frozenset(code for code in SonyPSXCode if code not in _P002J_ONLY_COMMANDS),
)

PSX_LATER_MODELS = PSXModel(
    name=("PSX later models (DESR-5500, DESR-7500, DESR-5700, and DESR-7700)"),
    codes=frozenset(code for code in SonyPSXCode if code not in _P001_ONLY_COMMANDS),
)

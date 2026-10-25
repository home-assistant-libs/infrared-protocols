"""Command codes for NAD CD players.

Codes are taken from the IRDB, from NAD CD player remotes and from the CD keys
on NAD receiver and amplifier remotes. All NAD components share one NEC
address, so amplifiers and receivers ignore these codes and the CD player responds.
"""

from enum import IntEnum

from ...commands import Command
from ...commands.nec import NECCommand

NAD_CD_ADDRESS = 0x7C87


class NADCDCode(IntEnum):
    """NAD CD player IR command codes."""

    PLAY = 0x01
    STOP = 0x02
    RANDOM = 0x03
    SCAN_BACK = 0x04
    SKIP_BACK = 0x05
    SKIP_FORWARD = 0x06
    SCAN_FORWARD = 0x07
    TIME = 0x08
    REPEAT = 0x0A
    PROGRAM = 0x0B
    REVIEW = 0x14
    NEXT_DISC = 0x17
    PAUSE = 0x4A
    EDIT = 0x4B
    OPEN_CLOSE = 0x48
    CLEAR = 0x50

    NUM_0 = 0x16
    NUM_1 = 0x0C
    NUM_2 = 0x0D
    NUM_3 = 0x0E
    NUM_4 = 0x0F
    NUM_5 = 0x10
    NUM_6 = 0x11
    NUM_7 = 0x12
    NUM_8 = 0x13
    NUM_9 = 0x15
    NUM_10 = 0x4C
    PLUS_10 = 0x4D

    DISC_1 = 0x41
    DISC_2 = 0x42
    DISC_3 = 0x43
    DISC_4 = 0x44
    DISC_5 = 0x45

    def to_command(self) -> Command:
        """Build an NEC command for this NAD CD player code."""
        return NECCommand(address=NAD_CD_ADDRESS, command=self.value)

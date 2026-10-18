"""Command codes for NAD cassette decks.

Codes are taken from the IRDB, from NAD cassette deck remotes and from the tape
keys on NAD receiver and amplifier remotes. All NAD components share one NEC
address. Dual-cassette decks use both sets; single-cassette decks respond to
the deck B codes.
"""

from enum import IntEnum

from ...commands import Command
from ...commands.nec import NECCommand

NAD_TAPE_ADDRESS = 0x7C87


class NADTapeCode(IntEnum):
    """NAD cassette deck IR command codes."""

    DECK_A_STOP = 0x52
    DECK_A_PLAY = 0x53
    DECK_A_REVERSE_PLAY = 0x54
    DECK_A_RECORD = 0x55
    DECK_A_FAST_FORWARD = 0x56
    DECK_A_REWIND = 0x57

    DECK_B_PAUSE = 0x99
    DECK_B_RECORD = 0x9A
    DECK_B_PLAY = 0x9C
    DECK_B_FAST_FORWARD = 0x9D
    DECK_B_REWIND = 0x9E
    DECK_B_STOP = 0x9F
    DECK_B_REVERSE_PLAY = 0xDE

    def to_command(self) -> Command:
        """Build an NEC command for this NAD cassette deck code."""
        return NECCommand(address=NAD_TAPE_ADDRESS, command=self.value)

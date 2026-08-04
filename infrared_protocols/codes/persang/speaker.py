"""Command codes for Persang speakers.

Captured from the remote shipped with a Persang Octane 9. Persang sells the same
handset as a spare for its other Bluetooth speakers, so other models are likely
to share these codes, but only the Octane 9 has been verified.
"""

from enum import IntEnum

from ...commands import Command
from ...commands.nec import NECCommand

PERSANG_ADDRESS = 0x80


class PersangSpeakerCode(IntEnum):
    """Persang speaker IR command codes."""

    EQ = 0x09
    MODE = 0x1A
    MUTE = 0x1E
    NEXT = 0x03
    NUM_0 = 0x07
    NUM_1 = 0x0A
    NUM_2 = 0x1B
    NUM_3 = 0x1F
    NUM_4 = 0x0C
    NUM_5 = 0x0D
    NUM_6 = 0x0E
    NUM_7 = 0x00
    NUM_8 = 0x0F
    NUM_9 = 0x19
    PLAY_PAUSE = 0x01
    POWER = 0x12
    PREVIOUS = 0x02
    REPEAT = 0x08
    SCAN = 0x04
    VOLUME_DOWN = 0x05
    VOLUME_UP = 0x06

    def to_command(self, repeat_count: int = 0) -> Command:
        """Build an NEC command for this Persang speaker code."""
        return NECCommand(
            address=PERSANG_ADDRESS, command=self.value, repeat_count=repeat_count
        )

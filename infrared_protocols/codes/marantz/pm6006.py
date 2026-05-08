"""Command codes for the Marantz PM6006 integrated amplifier."""

from enum import Enum

from ...commands import Command
from ...commands.marantz_extended import MarantzExtendedCommand
from ...commands.rc5 import RC5Command


class MarantzPM6006Code(Enum):
    """Marantz PM6006 IR command codes."""

    # System 0x10 (Audio Amplifier)
    POWER = (0x10, 0x0C)
    MUTE = (0x10, 0x0D)
    VOLUME_UP = (0x10, 0x10)
    VOLUME_DOWN = (0x10, 0x11)
    SPEAKER_AB = (0x10, 0x1D)
    SOURCE_DIRECT = (0x10, 0x22)
    LOUDNESS = (0x10, 0x32)

    # Analog source selection.
    SOURCE_CD = (0x14, 0x3F)
    SOURCE_CDR = (0x1A, 0x3F)
    SOURCE_PHONO = (0x15, 0x3F)
    SOURCE_TUNER = (0x11, 0x3F)

    # SOURCE_OPTICAL toggles between the two optical inputs on the amplifier.
    SOURCE_OPTICAL = (0x10, 0x01, 0x28)
    SOURCE_NETWORK = (0x19, 0x3F, 0x0A)
    SOURCE_COAX = (0x10, 0x01, 0x19)

    def to_command(self, repeat_count: int = 0, *, toggle: int = 0) -> Command:
        """Build the IR command for this Marantz PM6006 code."""
        code_tuple = self.value
        if len(code_tuple) == 3:
            address, command, extension = code_tuple
            return MarantzExtendedCommand(
                address=address,
                command=command,
                extension=extension,
                toggle=toggle,
                repeat_count=repeat_count,
            )

        if len(code_tuple) != 2:
            raise ValueError("Marantz PM6006 codes must define exactly 2 or 3 values")

        address, command = code_tuple
        return RC5Command(
            address=address,
            command=command,
            toggle=toggle,
            repeat_count=repeat_count,
        )

"""Shared IR command codes for Marantz audio amplifiers and receivers.

Codes are unioned across publicly documented Marantz remotes (PM6006, RC042SR,
SR-19, SR-7000/7300, SR7200, SR670, AV-9000). Not every model responds to
every code; see ``models.py`` for per-model support.
"""

from enum import Enum

from ...commands import Command
from ...commands.marantz_extended import MarantzExtendedCommand
from ...commands.rc5 import RC5Command


class MarantzAudioCode(Enum):
    """IR command code for a Marantz audio amplifier or receiver.

    The tuple value is one of:

    - ``(address, command)`` — a standard RC-5 frame. A ``command`` with
      bit 6 set is sent using the RC5X extended encoding.
    - ``(address, command, extension)`` — a Marantz extended frame.
    """

    # System 0x10 — audio amplifier / receiver
    POWER = (0x10, 0x0C)
    POWER_ON = (0x10, 0x0C, 0x01)
    POWER_OFF = (0x10, 0x0C, 0x02)
    MUTE = (0x10, 0x0D)
    MUTE_ON = (0x10, 0x0D, 0x00)
    MUTE_OFF = (0x10, 0x0D, 0x01)
    DISPLAY = (0x10, 0x0F)
    VOLUME_UP = (0x10, 0x10)
    VOLUME_DOWN = (0x10, 0x11)
    BASS_UP = (0x10, 0x16)
    BASS_DOWN = (0x10, 0x17)
    TREBLE_UP = (0x10, 0x18)
    TREBLE_DOWN = (0x10, 0x19)
    SPEAKER_AB = (0x10, 0x1D)
    SOURCE_DIRECT = (0x10, 0x22)
    DSP_MODE = (0x10, 0x25)
    SLEEP = (0x10, 0x26)
    FAST_FORWARD = (0x10, 0x2B)
    REWIND = (0x10, 0x2C)
    LOUDNESS = (0x10, 0x32)
    INPUT_CYCLE = (0x10, 0x40)
    SURROUND_UP = (0x10, 0x41)
    SURROUND_DOWN = (0x10, 0x42)
    # Cursor pad (RC5X — command bit 6 set).
    CURSOR_UP = (0x10, 0x50)
    CURSOR_DOWN = (0x10, 0x51)
    CURSOR_OK = (0x10, 0x52)
    CURSOR_EXIT = (0x10, 0x53)
    CURSOR_LEFT = (0x10, 0x55)
    CURSOR_RIGHT = (0x10, 0x56)
    CURSOR_ENTER = (0x10, 0x57)
    CENTER_LEVEL_UP = (0x10, 0x66)
    CENTER_LEVEL_DOWN = (0x10, 0x67)
    DELAY = (0x10, 0x68)

    # System 0x11 — tuner
    TUNER_PRESET_UP = (0x11, 0x20)
    TUNER_PRESET_DOWN = (0x11, 0x21)
    TUNER_MODE = (0x11, 0x25)
    TUNER_MEMORY = (0x11, 0x29)
    TUNER_SCAN = (0x11, 0x2B)
    TUNER_FM = (0x11, 0x2D)
    TUNER_AM = (0x11, 0x2E)
    TUNER_LW = (0x11, 0x2F)
    TUNER_CLEAR = (0x11, 0x3A)

    # System 0x00 — TV / global
    CHANNEL_UP = (0x00, 0x20)
    CHANNEL_DOWN = (0x00, 0x21)
    INPUT = (0x00, 0x38)

    # Source selection — RC-5 command 0x3F under each device's system address.
    SOURCE_TV = (0x00, 0x3F)
    SOURCE_VCR1 = (0x05, 0x3F)
    SOURCE_SAT = (0x06, 0x3F)
    SOURCE_LD = (0x0C, 0x3F)
    SOURCE_TUNER = (0x11, 0x3F)
    SOURCE_TAPE = (0x12, 0x3F)
    SOURCE_CD = (0x14, 0x3F)
    SOURCE_PHONO = (0x15, 0x3F)
    SOURCE_MD = (0x17, 0x3F)
    SOURCE_CDR = (0x1A, 0x3F)

    # RC5X source selectors (command 0x63) — newer Marantz remotes use these
    # for buttons commonly relabelled to digital inputs (Optical 1, TV optical).
    SOURCE_CBL_SAT = (0x06, 0x63)
    SOURCE_TV_AUDIO = (0x00, 0x63)

    # Marantz extended — digital inputs.
    SOURCE_OPTICAL = (0x10, 0x01, 0x28)
    SOURCE_COAX = (0x10, 0x01, 0x19)
    SOURCE_NETWORK = (0x19, 0x3F, 0x0A)

    # Marantz extended — auxiliary / DVD source slots.
    SOURCE_DVD = (0x16, 0x00, 0x10)
    SOURCE_AUX_1 = (0x16, 0x00, 0x06)
    SOURCE_AUX_2 = (0x16, 0x00, 0x07)
    SOURCE_AUX_3 = (0x16, 0x00, 0x08)
    SOURCE_AUX_4 = (0x16, 0x02, 0x00)
    SOURCE_AUX_5 = (0x16, 0x02, 0x01)
    SOURCE_AUX_6 = (0x16, 0x02, 0x02)
    SOURCE_AUX_7 = (0x16, 0x02, 0x03)

    def to_command(self, repeat_count: int = 0, *, toggle: int = 0) -> Command:
        """Build the IR command for this code."""
        if len(self.value) == 3:
            address, command, extension = self.value
            return MarantzExtendedCommand(
                address=address,
                command=command,
                extension=extension,
                toggle=toggle,
                repeat_count=repeat_count,
            )
        address, command = self.value
        return RC5Command(
            address=address,
            command=command,
            toggle=toggle,
            repeat_count=repeat_count,
        )

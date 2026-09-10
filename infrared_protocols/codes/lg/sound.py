"""Command codes for LG soundsystems (device id 0x3434) using Samsung32 protocol."""

from enum import IntEnum

from ...commands import Command
from ...commands.samsung import Samsung32Command


class LGSoundCode(IntEnum):
    """LG soundsystem IR command codes."""

    POWER_TOGGLE = 0x78
    POWER_ON = 0x20
    POWER_OFF = 0x9F

    INPUT = 0x51
    ENTER = 0x55

    NUM_0 = 0x2D
    NUM_1 = 0x82
    NUM_2 = 0x42
    NUM_3 = 0xC2
    NUM_4 = 0x22
    NUM_5 = 0xA2
    NUM_6 = 0x62
    NUM_7 = 0xE2
    NUM_8 = 0x12
    NUM_9 = 0x92

    LEFT = 0x15
    RIGHT = 0x95
    UP = 0xE5
    DOWN = 0x65

    VOLUME_UP = 0xE8
    VOLUME_DOWN = 0x68
    SPEAKER_LEVEL = 0x66
    MUTE = 0x00

    RED = 0x36
    GREEN = 0xB6
    YELLOW = 0x76
    BLUE = 0xF6

    HOME = 0xA5
    BACK = 0x45

    INPUT_OPTICAL = 0x6D
    INPUT_RADIO = 0x6F
    INPUT_IPOD = 0x9D

    EJECT = 0x59
    REPEAT = 0xCD
    SOUND_EFFECT = 0xF4

    @staticmethod
    def _mirror_byte(b: int) -> int:
        """(MSB<->LSB)."""
        b = (b & 0x0F) << 4 | b >> 4 & 0x0F
        b = (b & 0x33) << 2 | b >> 2 & 0x33
        return (b & 0x55) << 1 | b >> 1 & 0x55

    def to_command(self, repeat_count: int = 0) -> Command:
        """Build a Samsung32 command for this LG soundsystem code."""
        return Samsung32Command(
            address=self._mirror_byte(0x34),
            command=self._mirror_byte(self.value),
            repeat_count=repeat_count,
        )

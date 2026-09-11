"""Command codes for the Alpha Bidet JX-2 washlet (Kaseikyo protocol)."""

from enum import Enum

from ...commands import Command
from ...commands.kaseikyo import KaseikyoCommand

ALPHA_BIDET_ADDRESS = 0x0040

# 37 kHz fits the captured timings better than the Kaseikyo default of 38 kHz.
ALPHA_BIDET_MODULATION = 37000

# Every press is transmitted as two identical frames.
FRAME_COUNT = 2

# Absolute levels occupy the low nibble of the value byte; its high nibble is constant.
LEVEL_BASE = 0x20
MAX_LEVEL = 3


def _to_command(payload: bytes) -> Command:
    """Build the two-frame Kaseikyo command for a payload."""
    return KaseikyoCommand(
        address=ALPHA_BIDET_ADDRESS,
        data=[payload] * FRAME_COUNT,
        error_correction=AlphaBidetJX2Code.error_correction,
        modulation=ALPHA_BIDET_MODULATION,
    )


class AlphaBidetJX2Code(Enum):
    """Alpha Bidet JX-2 IR command codes, as the payload bytes before the checksum."""

    STOP = (0x10, 0xD0, 0x04, 0x95)
    # Holding stop sends its own function byte rather than repeating the frame.
    STOP_HOLD = (0x10, 0xD0, 0x44, 0x26)
    REAR = (0x10, 0xD0, 0x05, 0x92)
    FRONT = (0x10, 0xD0, 0x06, 0x92)
    DRY = (0x10, 0xD0, 0x07, 0x21)
    WASH_AND_DRY = (0x10, 0xD0, 0x36, 0x12)
    EASY_WASH = (0x10, 0xD0, 0x77, 0x92)
    WATER_DRY_UP = (0x10, 0xD0, 0x11, 0x22)
    WATER_DRY_DOWN = (0x10, 0xD0, 0x01, 0x21)
    # Nozzle position carries no value byte, so it steps rather than setting a position.
    NOZZLE_UP = (0x00, 0xD0, 0x18)
    NOZZLE_DOWN = (0x00, 0xD0, 0x08)

    @staticmethod
    def error_correction(data: bytes) -> bytes:
        """Calculate the checksum byte for Alpha Bidet JX-2 commands."""
        # The remote sums the payload nibbles without the parity merged into flags.
        payload = bytes([data[2] & 0xF0]) + data[3:]
        return bytes([sum((byte >> 4) + (byte & 0x0F) for byte in payload) & 0xFF])

    def to_command(self) -> Command:
        """Build the Kaseikyo command for this Alpha Bidet JX-2 code."""
        return _to_command(bytes(self.value))


class AlphaBidetJX2Setting(Enum):
    """Alpha Bidet JX-2 settings, as the payload bytes before the level byte."""

    WATER_TEMP = (0x10, 0xD0, 0x19)
    SEAT_TEMP = (0x10, 0xD0, 0x09)

    def to_command(self, level: int) -> Command:
        """Build the Kaseikyo command setting this setting to an absolute level."""
        if not 0 <= level <= MAX_LEVEL:
            raise ValueError(f"level must be between 0 and {MAX_LEVEL}, got {level}")

        return _to_command(bytes([*self.value, LEVEL_BASE | level]))

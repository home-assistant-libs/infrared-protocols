"""Command codes for Panasonic Ceiling Lights (Kaseikyo protocol)."""

from enum import Enum

from ...commands import Command
from ...commands.kaseikyo import KaseikyoCommand


class PanasonicCeilingLightCode(Enum):
    """Panasonic Ceiling Light IR command codes."""

    HIGH_CH1 = 0b001_01_010_0000
    HIGH_CH2 = 0b001_10_010_0000
    HIGH_CH3 = 0b001_11_010_0000
    LOW_CH1 = 0b001_01_011_0000
    LOW_CH2 = 0b001_10_011_0000
    LOW_CH3 = 0b001_11_011_0000
    FULL_CH1 = 0b001_01_100_0000
    FULL_CH2 = 0b001_10_100_0000
    FULL_CH3 = 0b001_11_100_0000
    ON_CH1 = 0b001_01_101_0000
    ON_CH2 = 0b001_10_101_0000
    ON_CH3 = 0b001_11_101_0000
    NIGHT_CH1 = 0b001_01_110_0000
    NIGHT_CH2 = 0b001_10_110_0000
    NIGHT_CH3 = 0b001_11_110_0000
    OFF_CH1 = 0b001_01_111_0000
    OFF_CH2 = 0b001_10_111_0000
    OFF_CH3 = 0b001_11_111_0000
    COOLEST_CH1 = 0b10001_01_0_0011
    COOLEST_CH2 = 0b10001_10_0_0011
    COOLEST_CH3 = 0b10001_11_0_0011
    WARMEST_CH1 = 0b10001_01_1_0011
    WARMEST_CH2 = 0b10001_10_1_0011
    WARMEST_CH3 = 0b10001_11_1_0011
    COOL_CH1 = 0b1001_000_0_0011
    COOL_CH2 = 0b1001_010_0_0011
    COOL_CH3 = 0b1001_100_0_0011
    WARM_CH1 = 0b1001_000_1_0011
    WARM_CH2 = 0b1001_010_1_0011
    WARM_CH3 = 0b1001_100_1_0011
    TIMER_CH1 = 0b101_00001_0011
    TIMER_CH2 = 0b101_01010_0011
    TIMER_CH3 = 0b101_10011_0011
    SET_CH1 = 0b11011_010_0011
    SET_CH2 = 0b11011_011_0011
    SET_CH3 = 0b11011_100_0011

    @staticmethod
    def error_correction(data: bytes) -> bytes:
        """Calculate error correction byte for Panasonic Ceiling Light commands."""
        # Error correction byte is the xor of data bytes except the address
        return bytes([data[2] ^ data[3]])

    def to_command(self, repeat_count: int = 0) -> Command:
        """Build an Kaseikyo command for this Panasonic Ceiling Light code."""
        return KaseikyoCommand(
            address=0x522C,
            data=[(self.value << 4).to_bytes(2, "little")],
            error_correction=self.error_correction,
            repeat_count=repeat_count,
            modulation=37000,
        )

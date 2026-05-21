"""Command codes for Panasonic Ceiling Lights (Kaseikyo protocol)."""

from enum import Enum

from ...commands import Command
from ...commands.kaseikyo import KaseikyoCommand


class PanasonicCeilingLightCode(Enum):
    """Panasonic Ceiling Light IR command codes."""

    HIGH_CH1 = 0x2A00
    HIGH_CH2 = 0x3200
    HIGH_CH3 = 0x3A00
    LOW_CH1 = 0x2B00
    LOW_CH2 = 0x3300
    LOW_CH3 = 0x3B00
    FULL_CH1 = 0x2C00
    FULL_CH2 = 0x3400
    FULL_CH3 = 0x3C00
    ON_CH1 = 0x2D00
    ON_CH2 = 0x3500
    ON_CH3 = 0x3D00
    NIGHT_CH1 = 0x2E00
    NIGHT_CH2 = 0x3600
    NIGHT_CH3 = 0x3E00
    OFF_CH1 = 0x2F00
    OFF_CH2 = 0x3700
    OFF_CH3 = 0x3F00
    COOLEST_CH1 = 0x8A30
    COOLEST_CH2 = 0x8C30
    COOLEST_CH3 = 0x8E30
    WARMEST_CH1 = 0x8B30
    WARMEST_CH2 = 0x8D30
    WARMEST_CH3 = 0x8F30
    COOL_CH1 = 0x9030
    COOL_CH2 = 0x9430
    COOL_CH3 = 0x9830
    WARM_CH1 = 0x9130
    WARM_CH2 = 0x9530
    WARM_CH3 = 0x9930
    TIMER_CH1 = 0xA130
    TIMER_CH2 = 0xAA30
    TIMER_CH3 = 0xB330
    SET_CH1 = 0xDA30
    SET_CH2 = 0xDB30
    SET_CH3 = 0xDC30

    @staticmethod
    def error_correction(data: bytes) -> bytes:
        """Calculate error correction byte for Panasonic Ceiling Light commands."""
        # Error correction byte is the xor of data bytes except the address
        return bytes([data[2] ^ data[3]])

    def to_command(self) -> Command:
        """Build an Kaseikyo command for this Panasonic Ceiling Light code."""
        return KaseikyoCommand(
            address=0x522C,
            data=self.value.to_bytes(2, "little"),
            error_correction=self.error_correction,
            modulation=37000,
        )

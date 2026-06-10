"""Command codes and state builders for Samsung Air Conditioners."""

from dataclasses import dataclass
from typing import Literal

from ...commands import Command
from ...commands.samsung import SamsungACCommand as StructuralACCommand


@dataclass(frozen=True)
class SamsungACStateBuilder:
    """Builder for Samsung AC IR commands (21-byte extended protocol)."""

    hvac_mode: Literal["off", "cool", "heat", "dry", "fan_only"]
    target_temperature: int
    fan_mode: Literal["auto", "low", "medium", "high"]

    def to_command(self) -> Command:
        """Compile the logical state into a 21-byte payload and generate the IR Command."""
        # Initialize a 21-byte array
        payload = [0x00] * 21

        # Block 1: Header and address (Fixed for this specific AC unit)
        payload[0:7] = [0x2A, 0x20, 0xF9, 0x00, 0x00, 0x00, 0x00]

        # Block 2: Base configuration (Fixed for this specific AC unit)
        payload[7:14] = [0xDF, 0x00, 0xE9, 0x07, 0x00, 0x00, 0x00]

        # Block 3: Dynamic state base initialization
        payload[14:21] = [0x80, 0x06, 0x00, 0x00, 0xC7, 0x00, 0x00]

        # Enforce temperature limits between 16°C and 30°C
        temp = max(16, min(30, self.target_temperature))

        # Full lookup table for Block 3 variable bytes based on captured physical remote data.
        # Structure: temp -> (Byte 16, Byte 17, Byte 19, Byte 20)
        temp_mapping: dict[int, tuple[int, int, int, int]] = {
            16: (0x88, 0xFB, 0x01, 0x54),
            17: (0x88, 0xFB, 0x41, 0x54),  # Interpolated checksum logic
            18: (0x88, 0xFB, 0x81, 0x54),  # Interpolated checksum logic
            19: (0x88, 0xFB, 0xC1, 0x54),  # Interpolated checksum logic
            20: (0x08, 0xFB, 0x01, 0x44),  # Interpolated checksum logic
            21: (0x08, 0xFB, 0x41, 0x44),  # Interpolated checksum logic
            22: (0x08, 0xFB, 0x81, 0x44),  # Interpolated checksum logic
            23: (0xC8, 0xFA, 0xC1, 0x55),
            24: (0x88, 0xFB, 0x01, 0x46),
            25: (0x48, 0xFB, 0xC7, 0x46),  # Fixed to 25°C capture variant (41/46 match)
            26: (0x08, 0xFB, 0x81, 0x56),
            27: (0xC8, 0xFA, 0xC1, 0x56),
            28: (0x88, 0xFA, 0x01, 0x57),  # Interpolated high-range logic
            29: (0x48, 0xFA, 0x41, 0x57),  # Interpolated high-range logic
            30: (0xC8, 0xFA, 0x81, 0x57),
        }

        # Retrieve values from mapping table
        b16, b17, b19, b20 = temp_mapping[temp]

        # Inject the mapped temperature and checksum bytes into Block 3
        payload[16] = b16
        payload[17] = b17
        payload[19] = b19
        payload[20] = b20

        return StructuralACCommand(payload=payload)
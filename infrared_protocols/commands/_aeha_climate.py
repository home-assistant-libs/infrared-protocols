"""AEHA framing for climate payloads represented in transmission bit order."""

from typing import Self, override

from ._climate import ClimatePacket
from .aeha import AehaCommand

_REVERSED = bytes(int(f"{value:08b}"[::-1], 2) for value in range(256))


class AehaClimatePacket(ClimatePacket):
    """Keep model payload fields while sharing AEHA's encoder and receiver windows."""

    @override
    def get_raw_timings(self) -> list[int]:
        """Convert the model's MSB byte view to AEHA's native LSB byte view."""
        return AehaCommand(data=self.data.translate(_REVERSED)).get_raw_timings()[:-1]

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode AEHA before validating the model signature and checksum."""
        packet = AehaCommand.from_raw_timings(timings)
        if packet is None:
            return None
        try:
            command = cls.__new__(cls)
            ClimatePacket.__init__(command, data=packet.data.translate(_REVERSED))
            return command
        except ValueError:
            return None

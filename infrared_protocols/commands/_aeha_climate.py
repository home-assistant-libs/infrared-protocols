"""AEHA framing for climate payloads represented in transmission bit order."""

from typing import Self, override

from ._climate import ClimatePacket
from .aeha import AehaCommand

_REVERSED = bytes(int(f"{value:08b}"[::-1], 2) for value in range(256))


class AehaClimatePacket[StateT](ClimatePacket[StateT]):
    """Keep model payload fields while sharing AEHA's encoder and receiver windows."""

    HEADER = (AehaCommand.TIMING.leader_mark, -AehaCommand.TIMING.leader_space)

    @override
    def get_raw_timings(self) -> list[int]:
        """Convert the model's MSB byte view to AEHA's native LSB byte view."""
        data = self.data if self.LSB else self.data.translate(_REVERSED)
        return AehaCommand(data=data).get_raw_timings()[:-1]

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode AEHA before validating the model signature and checksum."""
        packet = AehaCommand.from_raw_timings(timings)
        if packet is None:
            return None
        frame_length = 3 + 16 * len(packet.data)
        if len(timings) not in (frame_length, frame_length + 1):
            return None
        try:
            command = cls.__new__(cls)
            data = packet.data if cls.LSB else packet.data.translate(_REVERSED)
            ClimatePacket.__init__(command, data=data)
            return command
        except ValueError:
            return None

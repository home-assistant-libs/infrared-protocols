"""Toto infrared commands with two parameter nibbles and an XOR checksum."""

from typing import Self, override

from . import Command
from ._timing import PulseTiming, Reader, bits, number

_TIMING = PulseTiming(600, 520, 1667)


class TotoCommand(Command):
    """Three identical Toto frames carrying the command and remote parameters."""

    def __init__(
        self,
        *,
        command: int,
        rc_code_1: int = 0,
        rc_code_2: int = 0,
        modulation: int = 38000,
    ) -> None:
        """Initialize the command and its two parameter nibbles."""
        bits(command, 8)
        bits(rc_code_1, 4)
        bits(rc_code_2, 4)
        super().__init__(modulation=modulation)
        self.command, self.rc_code_1, self.rc_code_2 = command, rc_code_1, rc_code_2

    @property
    def code(self) -> int:
        """Return the native LSB-first 16-bit code, e.g. 0x37BB for EC/D/D."""
        parameters = self.rc_code_1 << 4 | self.rc_code_2
        return int(f"{self.command:08b}"[::-1], 2) << 8 | int(
            f"{parameters:08b}"[::-1], 2
        )

    @override
    def get_raw_timings(self) -> list[int]:
        """Encode a complete frame."""
        parameters = self.rc_code_1 * 16 + self.rc_code_2
        payload = (parameters << 16) | (self.command << 8) | (parameters ^ self.command)
        frame = [
            6000,
            -3000,
            *_TIMING.encode(bits(0x2008, 15) + bits(payload, 24)),
            600,
        ]
        return frame + [-36000] + frame + [-36000] + frame

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode and verify the header and checksum."""
        r = Reader(timings=timings)
        try:
            packets: list[int] = []
            while True:
                r.expect(6000, -3000)
                header = number(r.read_bits(_TIMING, 15))
                payload = number(r.read_bits(_TIMING, 24))
                r.expect(600)
                parameters, command, checksum = payload.to_bytes(3, "big")
                if header != 0x2008 or parameters ^ command != checksum:
                    return None
                packets.append(payload)
                if len(timings) - r.pos <= 1:
                    break
                r.expect(-36000)
            r.end()
            if any(value != packets[0] for value in packets[1:]):
                return None
            return cls(
                command=command, rc_code_1=parameters >> 4, rc_code_2=parameters & 15
            )
        except ValueError:
            return None

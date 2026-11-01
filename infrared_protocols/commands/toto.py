"""Toto infrared commands with two parameter nibbles and an XOR checksum."""

from typing import Self, override

from . import Command
from ._timing import PulseTiming, Reader, bits, number

_TIMING = PulseTiming(550, 550, 1700)


class TotoCommand(Command):
    """One Toto command frame; parameters retain their protocol meanings."""

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

    @override
    def get_raw_timings(self) -> list[int]:
        """Encode a complete frame."""
        parameters = self.rc_code_1 * 16 + self.rc_code_2
        payload = (parameters << 16) | (self.command << 8) | (parameters ^ self.command)
        return [6200, -2800, *_TIMING.encode(bits(0x2008, 15) + bits(payload, 24)), 550]

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode and verify the header and checksum."""
        r = Reader(timings)
        try:
            r.expect(6200, -2800)
            header = number(r.read_bits(_TIMING, 15))
            payload = number(r.read_bits(_TIMING, 24))
            r.expect(550)
            r.end()
            parameters, command, checksum = payload.to_bytes(3, "big")
            if header != 0x2008 or parameters ^ command != checksum:
                return None
            return cls(
                command=command, rc_code_1=parameters >> 4, rc_code_2=parameters & 15
            )
        except ValueError:
            return None

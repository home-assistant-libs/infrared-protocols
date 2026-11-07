"""Internal framing for fixed-length climate state packets."""

from dataclasses import dataclass
from typing import ClassVar, Self, override

from . import Command
from ._timing import (
    PulseTiming,
    Reader,
    byte_bits,
    capture_gap_options,
    join_captures,
    pack_bytes,
)


@dataclass(frozen=True)
class FramePart:
    """A byte block, its leader, and the gap following its stop mark."""

    length: int
    header: tuple[int, ...] = ()
    gap: int = 0


class ClimatePacket[StateT](Command):
    """Preserve all received bytes, including settings outside the decoded state."""

    HEADER: ClassVar[tuple[int, ...]]
    TIMING: ClassVar[PulseTiming]
    LENGTH: ClassVar[int]
    LSB: ClassVar[bool] = True
    GAP: ClassVar[int] = 0
    PARTS: ClassVar[tuple[FramePart, ...]] = ()
    COPIES: ClassVar[int] = 1
    REPEAT_GAP: ClassVar[int] = 0
    data: bytes

    def __init__(self, *, data: bytes, modulation: int = 38000) -> None:
        """Validate the complete wire packet and extract its decoded state."""
        super().__init__(modulation=modulation)
        self.data = bytes(data)
        self.parse(self.data)

    @property
    def state(self) -> StateT:
        """Decode the current payload, including changes made after construction."""
        return self.parse(self.data)

    @classmethod
    def parse(cls, data: bytes) -> StateT:
        """Decode the protocol-specific state."""
        raise NotImplementedError

    @classmethod
    def _validate_packet(cls, data: bytes) -> None:
        """Validate packet size and checksum before reading fields."""
        if len(data) != cls.LENGTH or cls.checksum(data[:-1]) != data[-1]:
            raise ValueError("invalid climate packet length or checksum")

    @staticmethod
    def checksum(data: bytes) -> int:
        """Return an additive checksum."""
        return sum(data) & 255

    @classmethod
    def _parts(cls) -> tuple[FramePart, ...]:
        return cls.PARTS or (FramePart(cls.LENGTH, cls.HEADER, cls.GAP),)

    @override
    def get_raw_timings(self) -> list[int]:
        """Encode every section and each protocol-mandated packet copy."""
        packet: list[int] = []
        offset = 0
        for part in self._parts():
            data = self.data[offset : offset + part.length]
            packet.extend(
                (
                    *part.header,
                    *self.TIMING.encode(byte_bits(data, lsb=self.LSB)),
                    self.TIMING.mark,
                )
            )
            if part.gap:
                packet.append(-part.gap)
            offset += part.length
        result = packet.copy()
        for _ in range(self.COPIES - 1):
            result.extend((-self.REPEAT_GAP, *packet))
        return result

    @classmethod
    def _read_packet(cls, reader: Reader) -> bytes:
        parts = cls._parts()
        data = bytearray()
        for i, part in enumerate(parts):
            reader.expect(*part.header)
            data.extend(
                pack_bytes(reader.read_bits(cls.TIMING, part.length * 8), lsb=cls.LSB)
            )
            reader.expect(cls.TIMING.mark)
            if i < len(parts) - 1:
                reader.expect(-part.gap)
        return bytes(data)

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode complete sections and verify any repeated copies agree.

        Receivers may stop at an inter-frame gap, so a single complete packet
        is accepted even for protocols whose transmitters send it twice.
        """
        reader = Reader(timings=timings)
        try:
            data = cls._read_packet(reader)
            for _ in range(cls.COPIES - 1):
                if len(timings) - reader.pos <= 1:
                    break
                reader.expect(-cls.REPEAT_GAP)
                if cls._read_packet(reader) != data:
                    raise ValueError("repeated climate state differs")
            reader.end(min_gap=min(3000, round(cls._parts()[-1].gap * 0.6)) or 3000)
            command = cls.__new__(cls)
            ClimatePacket.__init__(command, data=data)
            return command
        except ValueError:
            return None

    @classmethod
    def from_raw_captures(
        cls, captures: list[list[int]], *, idle: int = 10000
    ) -> Self | None:
        """Decode consecutive bursts of one press split by a receiver idle timeout.

        Supply all sections in order; incomplete or corrupt presses return None.
        A single complete transmitted copy suffices for repeated commands.
        """
        if idle < 3000:
            raise ValueError("idle must be at least 3000 microseconds")
        if len(captures) == 1:
            return cls.from_raw_timings(captures[0])
        if not captures:
            return None
        parts = cls._parts()
        packet_gaps: list[int] = []
        for index, part in enumerate(parts):
            packet_gaps.extend(-t for t in part.header if t < 0)
            if index < len(parts) - 1 and part.gap:
                packet_gaps.append(part.gap)
        gaps = packet_gaps.copy()
        for _ in range(cls.COPIES):
            for selected in capture_gap_options(
                tuple(gaps), idle=idle, count=len(captures) - 1
            ):
                try:
                    result = cls.from_raw_timings(join_captures(captures, selected))
                except ValueError:
                    continue
                if result is not None:
                    return result
            if cls.REPEAT_GAP:
                gaps.append(cls.REPEAT_GAP)
            gaps.extend(packet_gaps)
        return None

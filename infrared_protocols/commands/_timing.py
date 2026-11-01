"""Internal building blocks for signed infrared pulse sequences."""

from collections.abc import Iterable
from dataclasses import dataclass


def bits(value: int, width: int, *, lsb: bool = False) -> list[int]:
    """Expand an unsigned field in transmission order."""
    if not 0 <= value < 1 << width:
        raise ValueError(f"value must fit in {width} bits")
    positions = range(width) if lsb else range(width - 1, -1, -1)
    return [(value >> position) & 1 for position in positions]


def number(values: Iterable[int], *, lsb: bool = False) -> int:
    """Pack a field from transmission order."""
    values = list(values)
    return sum(bit << i for i, bit in enumerate(values if lsb else reversed(values)))


def byte_bits(data: bytes, *, lsb: bool = True) -> list[int]:
    """Expand bytes without changing their order."""
    return [bit for byte in data for bit in bits(byte, 8, lsb=lsb)]


def pack_bytes(values: list[int], *, lsb: bool = True) -> bytes:
    """Pack complete bytes from transmitted bits."""
    if len(values) % 8:
        raise ValueError("incomplete byte")
    return bytes(number(values[i : i + 8], lsb=lsb) for i in range(0, len(values), 8))


def close(actual: int, expected: float, tolerance: float = 0.25) -> bool:
    """Match a duration including its polarity."""
    return abs(actual - expected) <= abs(expected) * tolerance


def runs(levels: Iterable[int], unit: int) -> list[int]:
    """Merge adjacent levels into signed durations."""
    result: list[int] = []
    for level in levels:
        duration = unit if level else -unit
        if result and (result[-1] > 0) == (duration > 0):
            result[-1] += duration
        else:
            result.append(duration)
    return result


@dataclass(frozen=True)
class PulseTiming:
    """A zero and one mark/space pair, measured in microseconds."""

    mark: int
    zero: int
    one: int
    one_mark: int | None = None

    def encode(self, values: Iterable[int]) -> list[int]:
        """Encode bits as mark/space pairs."""
        return [
            duration
            for bit in values
            for duration in (
                (self.one_mark or self.mark) if bit else self.mark,
                -(self.one if bit else self.zero),
            )
        ]


class Reader:
    """Consume a capture; malformed or truncated input raises ValueError."""

    def __init__(self, timings: list[int]) -> None:
        """Retain the capture and a cursor into it."""
        self.timings = timings
        self.pos = 0

    def expect(self, *durations: int) -> None:
        """Consume a fixed sequence with receiver tolerance."""
        for expected in durations:
            if self.pos >= len(self.timings) or not close(
                self.timings[self.pos], expected
            ):
                raise ValueError("unexpected or missing pulse")
            self.pos += 1

    def read_bits(
        self, timing: PulseTiming, count: int, *, last_space_optional: bool = False
    ) -> list[int]:
        """Read exactly count bits, rejecting ambiguous symbols."""
        result: list[int] = []
        for i in range(count):
            if self.pos >= len(self.timings):
                raise ValueError("truncated field")
            mark = self.timings[self.pos]
            candidates = [
                bit
                for bit in (0, 1)
                if close(mark, (timing.one_mark or timing.mark) if bit else timing.mark)
            ]
            if self.pos + 1 < len(self.timings):
                space = self.timings[self.pos + 1]
                candidates = [
                    bit
                    for bit in candidates
                    if close(space, -(timing.one if bit else timing.zero))
                ]
                self.pos += 2
            elif last_space_optional and i == count - 1:
                self.pos += 1
            else:
                raise ValueError("missing bit space")
            if len(candidates) != 1:
                raise ValueError("invalid bit")
            result.append(candidates[0])
        return result

    def end(self, *, min_gap: int = 3000) -> None:
        """Accept the end of capture or one trailing idle space."""
        tail = self.timings[self.pos :]
        if tail and not (len(tail) == 1 and tail[0] <= -min_gap):
            raise ValueError("unexpected trailing pulses")

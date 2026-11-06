"""Internal building blocks for signed infrared pulse sequences."""

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from itertools import combinations


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


def close(
    actual: int, expected: float, tolerance: float = 0.25, *, absolute: float = 0
) -> bool:
    """Match a duration including its polarity."""
    return (
        (actual > 0) == (expected > 0)
        and actual != 0
        and abs(actual - expected) <= max(abs(expected) * tolerance, absolute)
    )


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


def capture_gap_options(
    gaps: tuple[int, ...], *, idle: int, count: int
) -> Iterator[tuple[int, ...]]:
    """Select possible receiver boundaries within the decoder's timing tolerance."""
    eligible = tuple(gap for gap in gaps if max(gap * 1.25, gap + 225) >= idle)
    yield from dict.fromkeys(combinations(eligible, count))


def join_captures(captures: list[list[int]], gaps: tuple[int, ...]) -> list[int]:
    """Join one press split at receiver idle timeouts using its protocol gaps.

    The caller groups consecutive bursts from one press. A reported idle timeout
    is a lower bound, so replace it with the protocol's known section gap.
    The complete command decoder still validates every section and checksum.
    """
    if len(captures) != len(gaps) + 1:
        raise ValueError("incorrect number of receiver bursts")
    result: list[int] = []
    for index, capture in enumerate(captures):
        body = capture[:-1] if capture and capture[-1] <= -3000 else capture
        if not body or body[0] <= 0 or body[-1] <= 0:
            raise ValueError("incomplete receiver burst")
        if index:
            result.append(-gaps[index - 1])
        result.extend(body)
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

    def __init__(self, *, timings: list[int], tolerance: float = 0.25) -> None:
        """Retain the capture and a cursor into it."""
        self.timings = timings
        self.pos = 0
        self.tolerance = tolerance

    def expect(self, *durations: int) -> None:
        """Consume a fixed sequence with receiver tolerance."""
        for expected in durations:
            if self.pos >= len(self.timings) or not close(
                self.timings[self.pos], expected, self.tolerance, absolute=225
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
            one_mark = timing.one_mark or timing.mark
            mark_window = (
                min(225, abs(one_mark - timing.mark) / 2 - 1)
                if one_mark != timing.mark
                else 225
            )
            candidates = [
                bit
                for bit in (0, 1)
                if close(
                    mark,
                    one_mark if bit else timing.mark,
                    self.tolerance,
                    absolute=mark_window,
                )
            ]
            final = last_space_optional and i == count - 1
            if self.pos + 1 < len(self.timings):
                space = self.timings[self.pos + 1]
                if final and self.pos + 2 == len(self.timings) and len(candidates) == 1:
                    expected = timing.one if candidates[0] else timing.zero
                    if space > -expected * (1 - self.tolerance):
                        raise ValueError("short final bit space")
                else:
                    space_window = (
                        min(350, abs(timing.one - timing.zero) / 2 - 1)
                        if timing.one != timing.zero
                        else 350
                    )
                    candidates = [
                        bit
                        for bit in candidates
                        if close(
                            space,
                            -(timing.one if bit else timing.zero),
                            self.tolerance,
                            absolute=space_window,
                        )
                    ]
                self.pos += 2
            elif final:
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

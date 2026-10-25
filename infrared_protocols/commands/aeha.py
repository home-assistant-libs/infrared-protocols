"""AEHA format IR command.

Everything is expressed in multiples of a base
time unit T, nominally 425 us but allowed anywhere between 350 and 500:

  leader:   8T mark, 4T space
  bit:      1T mark, then 1T space for a zero and 3T space for a one
  trailer:  1T mark, then a long space

Payload bytes are sent least-significant bit first. What those bytes mean is left to the
protocol built on top: this module only carries them.

Vendors round the base unit differently, and some do not keep a single one across the
leader and the bits, so the timings are a value object a subclass overrides rather than
constants derived from T.
"""

from dataclasses import dataclass
from typing import ClassVar, override

from . import Command

_NOMINAL_BASE_UNIT = 425
"""Nominal base time unit for AEHA, in microseconds."""


@dataclass(frozen=True, slots=True)
class AehaTiming:
    """Physical-layer timings for one AEHA variant, in microseconds.

    The defaults are the nominal AEHA values. The tolerances are deliberately
    asymmetric: an IR receiver's AGC distorts marks far more than spaces, so the mark
    only has to be plausible and the space is what decides the bit.

    The leader tolerances are a fraction of the expected duration, since the two
    leader parts differ by a factor of two and a single window cannot fit both. A
    receiver skews a bit by roughly a fixed number of microseconds rather than a fixed
    proportion, so the bit tolerances are absolute microseconds instead.

    The trailer gap is whatever the sender leaves before the next burst, so it is not
    matched against an expected duration: any space of at least min_trailer_space ends
    the frame. That floor only has to sit far above a one's space for no distorted bit
    to be mistaken for the end of the payload.
    """

    leader_mark: int = 8 * _NOMINAL_BASE_UNIT
    leader_space: int = 4 * _NOMINAL_BASE_UNIT
    bit_mark: int = _NOMINAL_BASE_UNIT
    zero_space: int = _NOMINAL_BASE_UNIT
    one_space: int = 3 * _NOMINAL_BASE_UNIT
    trailer_space: int = 8000
    min_trailer_space: int = 4000
    leader_mark_tolerance: float = 0.7
    leader_space_tolerance: float = 0.25
    bit_mark_tolerance: int = 350
    bit_space_tolerance: int = 350


AEHA_NOMINAL = AehaTiming()


def _is_close(actual: int, expected: int, tolerance: float) -> bool:
    """Check if a timing is within the given relative tolerance of the expected."""
    margin = expected * tolerance
    return expected - margin <= actual <= expected + margin


class AehaCommand(Command):
    """AEHA format IR command."""

    TIMING: ClassVar[AehaTiming] = AEHA_NOMINAL
    """Physical-layer timings for this AEHA variant."""

    data: bytes
    """Payload bytes, sent least-significant bit first."""

    def __init__(
        self,
        *,
        data: bytes,
        modulation: int = 38000,
    ) -> None:
        """Initialize the AEHA IR command."""
        super().__init__(modulation=modulation)
        self.data = data

    @override
    def get_raw_timings(self) -> list[int]:
        """Get raw timings for the AEHA command.

        AEHA protocol timing (in base time units):
        - T: base time unit (350µs - 500µs, 425µs typ.)
        - Leader pulse: 8T high, 4T low
        - Logical '0': 1T high, 1T low
        - Logical '1': 1T high, 3T low
        - End pulse: 1T high, then a long space

        Data format (variable length, LSB first).
        """
        timing = self.TIMING
        timings: list[int] = [timing.leader_mark, -timing.leader_space]
        for byte in self.data:
            for i in range(8):
                timings.append(timing.bit_mark)
                one = (byte >> i) & 1
                timings.append(-(timing.one_space if one else timing.zero_space))
        timings.append(timing.bit_mark)
        timings.append(-timing.trailer_space)
        return timings

    @classmethod
    def _decode_data(cls, timings: list[int]) -> bytes | None:
        """Decode raw IR timings into the payload bytes they carry.

        Returns the payload if the timings open with this variant's leader, carry a
        whole number of bytes and close with the trailer, or None otherwise. Anything
        else is rejected rather than cut short: a pair that decodes as neither a bit nor
        the trailer is corruption, and stopping there would hand back a prefix of the
        payload that looks just like a shorter message. A message truncated mid-byte
        cannot be trusted either.

        A capture that drops the final gap is still accepted, since some receivers stop
        recording at the last mark, and timings after the trailer are ignored, since a
        capture often runs on into the repeat that follows.
        """
        timing = cls.TIMING
        if len(timings) < 2:
            return None
        if not _is_close(
            timings[0], timing.leader_mark, timing.leader_mark_tolerance
        ) or not _is_close(
            abs(timings[1]), timing.leader_space, timing.leader_space_tolerance
        ):
            return None

        bits: list[int] = []
        index = 2
        while index < len(timings):
            mark = timings[index]
            has_space = index + 1 < len(timings)
            space = abs(timings[index + 1]) if has_space else None
            if space is None or space >= timing.min_trailer_space:
                if abs(mark - timing.bit_mark) > timing.bit_mark_tolerance:
                    return None
                break
            bit = cls._decode_bit(mark, space)
            if bit is None:
                return None
            bits.append(bit)
            index += 2
        else:
            return None

        if not bits or len(bits) % 8:
            return None
        return bytes(
            sum(bits[i + j] << j for j in range(8)) for i in range(0, len(bits), 8)
        )

    @classmethod
    def _decode_bit(cls, mark: int, space: int) -> int | None:
        """Decode one bit from its mark and space, or None if it matches neither."""
        timing = cls.TIMING
        if abs(mark - timing.bit_mark) > timing.bit_mark_tolerance:
            return None
        if abs(space - timing.zero_space) <= timing.bit_space_tolerance:
            return 0
        if abs(space - timing.one_space) <= timing.bit_space_tolerance:
            return 1
        return None

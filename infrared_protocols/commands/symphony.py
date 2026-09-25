"""Symphony IR command (rc_switch family).

Symphony is the protocol used by ceiling fans, coolers and similar
remotes with RF heritage, among them Silvercrest and Dreo fans.

Frame structure:
- No leader. A logical '1' is a 1260us mark and a 460us space, a logical
  '0' is a 460us mark and a 1260us space, most significant bit first.
- A frame is 8, 12 or 16 bits.
- A transmission is the frame re-sent while the button is held, with a
  footer gap of 4 * (460 + 1260) us after every frame.
- There is no checksum of any kind.

The missing checksum drives the two decode rules below. A capture is
accepted only when at least two frames agree, because one frame of
1260/460-shaped pulses is not evidence enough to tell Symphony from line
noise. The identity is then decided by majority vote across the frames,
which also discards the all-zeros and all-ones preamble frames several
Symphony remotes transmit ahead of the button code, along with truncated
tail frames. Relaxing either rule makes this decoder a false-match
machine, so both are load-bearing rather than defensive.
"""

from collections import Counter
from collections.abc import Callable, Sequence
from typing import Self, override

from . import Command

SHORT_US = 460
LONG_US = 1260
# Midpoint between the short and long pulse widths.
PULSE_MIDPOINT_US = 860
# A pulse outside this band is not a Symphony bit half.
PULSE_MIN_US = 180
PULSE_MAX_US = 2200
# Gap after every frame, including the last one.
FOOTER_GAP_US = 4 * (SHORT_US + LONG_US)
# Bit spaces top out at LONG_US, so a space this long separates frames.
FRAME_GAP_US = 4000
MODULATION_HZ = 38000
VALID_NBITS = (8, 12, 16)


def _split_frames(timings: Sequence[int], min_gap_us: int) -> list[list[int]]:
    """Split signed timings into frames at spaces of at least min_gap_us.

    The gap spaces themselves are dropped and every returned frame starts
    on a mark. A capture that ends without a trailing gap yields its final
    frame as-is, since captures routinely truncate the last footer space.
    """
    frames: list[list[int]] = []
    current: list[int] = []
    for value in timings:
        if value < 0 and -value >= min_gap_us:
            if current:
                frames.append(current)
                current = []
            continue
        if not current and value < 0:
            # A frame never starts on a space, so leading idle is dropped.
            continue
        current.append(value)
    if current:
        frames.append(current)
    return frames


def _majority(
    values: Sequence[tuple[int, int]],
) -> tuple[tuple[int, int], int] | None:
    """Return the most common value with its count, or None if empty.

    Ties resolve to the value seen first, which for a capture means the
    earliest decoded frame of the tied set.
    """
    if not values:
        return None
    return Counter(values).most_common()[0]


def _decode_frames_majority(
    frames: Sequence[Sequence[int]],
    decode_frame: Callable[[Sequence[int]], tuple[int, int] | None],
    *,
    min_votes: int,
) -> tuple[tuple[int, int], int] | None:
    """Decode every frame and majority-vote the results.

    Returns the winning value with its vote count, or None when no frame
    decodes or the winner has fewer than min_votes votes.
    """
    decoded = [d for d in (decode_frame(f) for f in frames) if d is not None]
    top = _majority(decoded)
    if top is None or top[1] < min_votes:
        return None
    return top


class SymphonyCommand(Command):
    """Symphony IR command (8, 12 or 16 bit, rc_switch family)."""

    # Symphony carries no checksum, so agreement between repeated frames is
    # the only integrity evidence there is; one decoded frame is not enough.
    MIN_FRAME_VOTES = 2

    data: int
    nbits: int

    def __init__(
        self,
        *,
        data: int,
        nbits: int = 12,
        modulation: int = MODULATION_HZ,
        repeat_count: int = 0,
    ) -> None:
        """Initialize the Symphony IR command."""
        if nbits not in VALID_NBITS:
            raise ValueError(f"nbits must be one of 8, 12 or 16, got {nbits}")
        if not 0 <= data < (1 << nbits):
            raise ValueError(f"data must fit in {nbits} bits, got {data:#x}")
        super().__init__(modulation=modulation, repeat_count=repeat_count)
        self.data = data
        self.nbits = nbits

    @override
    def get_raw_timings(self) -> list[int]:
        """Get raw timings for the Symphony command.

        Symphony protocol timing (in microseconds):
        - Logical '0': 460us high, 1260us low
        - Logical '1': 1260us high, 460us low
        - Frame: 8, 12 or 16 bits, most significant bit first, no leader
        - Footer gap: 6880us after every frame
        - Repeat: the full frame retransmitted on that footer gap

        The footer gap closes the last frame as well as the ones before
        it, which is how the hardware remotes pad every transmission.
        """
        frame: list[int] = []
        for i in range(self.nbits - 1, -1, -1):
            bit = (self.data >> i) & 1
            if bit:
                frame.extend([LONG_US, -SHORT_US])
            else:
                frame.extend([SHORT_US, -LONG_US])

        timings: list[int] = []
        for _ in range(self.repeat_count + 1):
            timings.extend(frame)
            timings.append(-FOOTER_GAP_US)
        return timings

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode raw IR timings into a SymphonyCommand.

        The whole capture is expected rather than one frame: the frames
        are split apart here, decoded independently and majority-voted,
        and repeat_count is derived from how many of them carried the
        winning value.

        Returns a SymphonyCommand when at least MIN_FRAME_VOTES frames
        agree, or None otherwise.
        """
        frames = _split_frames(timings, FRAME_GAP_US)
        result = _decode_frames_majority(
            frames, cls._decode_frame, min_votes=cls.MIN_FRAME_VOTES
        )
        if result is None:
            return None
        (data, nbits), votes = result
        return cls(data=data, nbits=nbits, repeat_count=votes - 1)

    @staticmethod
    def _decode_frame(frame: Sequence[int]) -> tuple[int, int] | None:
        """Decode one Symphony frame to its data value and bit count."""
        # Each bit is a mark and space pair; the final space may be the
        # stripped footer gap, so a frame ending on a mark is valid.
        marks = frame[0::2]
        spaces = frame[1::2]
        if len(marks) not in VALID_NBITS:
            return None

        bits: list[int] = []
        for index, mark in enumerate(marks):
            if mark <= 0 or not PULSE_MIN_US <= mark <= PULSE_MAX_US:
                return None
            long_mark = mark > PULSE_MIDPOINT_US
            if index < len(spaces):
                space = -spaces[index]
                if not PULSE_MIN_US <= space <= PULSE_MAX_US:
                    return None
                # Mark and space widths must disagree; an equal-width pair
                # is not a Symphony bit.
                if (space > PULSE_MIDPOINT_US) == long_mark:
                    return None
            bits.append(1 if long_mark else 0)

        data = 0
        for bit in bits:
            data = (data << 1) | bit
        return (data, len(bits))

"""Symphony IR command (rc_switch family).

Symphony is the protocol used by ceiling fans, coolers and similar
remotes with RF heritage, among them Silvercrest and Dreo fans.

Frame structure:
- No leader. A logical '1' is a 1260us mark and a 460us space, a logical
  '0' is a 460us mark and a 1260us space, most significant bit first.
- A frame is 12 bits: a 3-bit frame head, a 2-bit custom code and a 7-bit
  control word.
- A transmission is the frame re-sent while the button is held, with a
  footer gap of 4 * (460 + 1260) us after every frame.
- There is no checksum of any kind.

The missing checksum drives the two decode rules below. A capture is
accepted only when at least two frames agree, because one frame of
1260/460-shaped pulses is not evidence enough to tell Symphony from line
noise. The identity is then decided by majority vote across the frames.
Frames carrying a reserved control word (start frames) are left out of
the vote, and truncated tail frames lose it. Relaxing either rule makes
this decoder a false-match machine, so both are load-bearing rather than
defensive.
"""

from collections import Counter
from collections.abc import Sequence
from enum import IntEnum
from typing import ClassVar, Self, override

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
FRAME_BITS = 12
# Control words that never carry a key: XIN HUI start frames send 0x00 then
# 0x7F, and SM5021 remotes send 0x00 frames after the key is released.
RESERVED_CONTROL_WORDS = (0x00, 0x7F)


class SymphonyKey(IntEnum):
    """SM5021 datasheet key codes (control word values)."""

    K1 = 0x01
    K2 = 0x02
    K3 = 0x04
    K4 = 0x08
    K5 = 0x10
    K6 = 0x20
    K7 = 0x43
    K8 = 0x46


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


def _encode_frame(code: int) -> list[int]:
    """Encode one 12-bit frame, closed by the footer gap."""
    frame: list[int] = []
    for i in range(FRAME_BITS - 1, -1, -1):
        if (code >> i) & 1:
            frame.extend([LONG_US, -SHORT_US])
        else:
            frame.extend([SHORT_US, -LONG_US])
    # Remotes extend the last bit's space by the gap rather than sending
    # a second space, so the timings keep alternating mark and space.
    frame[-1] -= FOOTER_GAP_US
    return frame


class SymphonyCommand(Command):
    """Symphony IR command (12 bit, rc_switch family).

    The fields follow the SM5021 datasheet layout, most significant bit
    first: frame_head (3 bits), custom_code (2 bits), control_word (7 bits).
    from_code() and code take the same frame as one 12-bit value, the form
    other tools print and the one to use for remotes that do not follow the
    SM5021 layout.

    start_frames sends the two frames XIN HUI remotes put ahead of the
    button frames: control word 0x00 then 0x7F, with the same frame head and
    custom code. It only affects encoding.
    """

    MIN_FRAME_VOTES: ClassVar[int] = 2
    """Frames that must agree before a capture is accepted.

    Symphony carries no checksum, so agreement between repeated frames is
    the only integrity evidence there is; one decoded frame is not enough.
    """

    frame_head: int
    custom_code: int
    control_word: int
    start_frames: bool

    def __init__(
        self,
        *,
        custom_code: int,
        control_word: int,
        frame_head: int = 0b110,
        start_frames: bool = False,
        modulation: int = MODULATION_HZ,
        repeat_count: int = 0,
    ) -> None:
        """Initialize the Symphony IR command."""
        super().__init__(modulation=modulation, repeat_count=repeat_count)
        if not 0 <= frame_head <= 0b111:
            raise ValueError(
                f"frame_head must be a 3-bit value (0-7), got {frame_head:#x}"
            )
        if not 0 <= custom_code <= 0b11:
            raise ValueError(
                f"custom_code must be a 2-bit value (0-3), got {custom_code:#x}"
            )
        if not 0 <= control_word <= 0x7F:
            raise ValueError(
                f"control_word must be a 7-bit value (0-0x7F), got {control_word:#x}"
            )
        if control_word in RESERVED_CONTROL_WORDS:
            raise ValueError(
                f"control_word {control_word:#x} is reserved for start and release"
                " frames, not a key"
            )
        self.frame_head = frame_head
        self.custom_code = custom_code
        self.control_word = control_word
        self.start_frames = start_frames

    @classmethod
    def from_code(
        cls,
        code: int,
        *,
        start_frames: bool = False,
        modulation: int = MODULATION_HZ,
        repeat_count: int = 0,
    ) -> Self:
        """Create a SymphonyCommand from the 12-bit frame value."""
        if not 0 <= code <= 0xFFF:
            raise ValueError(f"code must be a 12-bit value (0-0xFFF), got {code:#x}")
        return cls(
            frame_head=code >> 9,
            custom_code=(code >> 7) & 0b11,
            control_word=code & 0x7F,
            start_frames=start_frames,
            modulation=modulation,
            repeat_count=repeat_count,
        )

    @property
    def code(self) -> int:
        """The 12-bit frame value, as other Symphony tools print it."""
        return self.frame_head << 9 | self.custom_code << 7 | self.control_word

    @override
    def get_raw_timings(self) -> list[int]:
        """Get raw timings for the Symphony command.

        Symphony protocol timing (in microseconds):
        - Logical '0': 460us high, 1260us low
        - Logical '1': 1260us high, 460us low
        - Frame: 12 bits, most significant bit first, no leader
        - Footer gap: 6880us after every frame, added to the last bit's space
        - Repeat: the full frame retransmitted on that footer gap

        The footer gap closes the last frame as well as the ones before
        it, which is how the hardware remotes pad every transmission.
        """
        timings: list[int] = []
        if self.start_frames:
            prefix = self.frame_head << 9 | self.custom_code << 7
            for control_word in RESERVED_CONTROL_WORDS:
                timings.extend(_encode_frame(prefix | control_word))
        timings.extend(_encode_frame(self.code) * (self.repeat_count + 1))
        return timings

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode raw IR timings into a SymphonyCommand.

        The whole capture is expected rather than one frame: the frames
        are split apart here, decoded independently and majority-voted,
        and repeat_count is derived from how many of them carried the
        winning value. Start frames are never reported.

        Returns a SymphonyCommand when at least MIN_FRAME_VOTES frames
        agree, or None otherwise.
        """
        codes = [
            code
            for code in map(cls._decode_frame, _split_frames(timings, FRAME_GAP_US))
            if code is not None and code & 0x7F not in RESERVED_CONTROL_WORDS
        ]
        if not codes:
            return None
        code, votes = Counter(codes).most_common()[0]
        if votes < cls.MIN_FRAME_VOTES:
            return None
        return cls.from_code(code, repeat_count=votes - 1)

    @staticmethod
    def _decode_frame(frame: Sequence[int]) -> int | None:
        """Decode one Symphony frame to its 12-bit value."""
        # Each bit is a mark and space pair; the final space may be the
        # stripped footer gap, so a frame ending on a mark is valid.
        marks = frame[0::2]
        spaces = frame[1::2]
        if len(marks) != FRAME_BITS:
            return None

        code = 0
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
            code = code << 1 | long_mark
        return code

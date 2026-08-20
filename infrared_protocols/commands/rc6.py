"""RC-6 IR command (Philips, Microsoft MCE, and other devices)."""

from typing import override

from . import Command

# RC-6 timing unit in microseconds: 16 carrier periods at 36 kHz. A normal bit
# spans two units, the trailer bit four, so its halves are double width.
RC6_UNIT_US = 444
# RC-6 carrier frequency in Hz.
RC6_MODULATION_HZ = 36000
# Leader: a 6 unit burst followed by a 2 unit space, opening every frame.
RC6_LEADER_MARK_US = 6 * RC6_UNIT_US
RC6_LEADER_SPACE_US = 2 * RC6_UNIT_US
# Time between the start of one frame and the start of the next while a key is
# held. The 6 unit signal-free time that closes a frame is only a minimum; the
# frame is padded out to this period.
RC6_REPEAT_PERIOD_US = 107000
# Mode 0 is the only mode in general consumer use, and its mode bits are zero.
RC6_MODE_0_BITS = (0, 0, 0)


def append_signed_us(timings: list[int], value: int) -> None:
    """Append a microsecond duration, merging into the last entry if same sign."""
    if timings and (timings[-1] > 0) == (value > 0):
        timings[-1] += value
    else:
        timings.append(value)


def manchester_encode_bit(timings: list[int], bit: int, half_bit_us: int) -> None:
    """Append the two Manchester half-bits for ``bit`` to ``timings``.

    RC-6 inverts the RC-5 convention: logic '1' is a burst followed by a
    space, logic '0' is a space followed by a burst. Adjacent halves of
    equal sign are merged.
    """
    if bit:
        append_signed_us(timings, half_bit_us)
        append_signed_us(timings, -half_bit_us)
    else:
        append_signed_us(timings, -half_bit_us)
        append_signed_us(timings, half_bit_us)


class RC6Command(Command):
    """RC-6 mode 0 IR command (Philips, Microsoft MCE, and similar devices).

    This is the protocol used by Philips televisions, by Windows Media Center
    remotes, and by set-top boxes from operators such as Comcast/Xfinity.

    Only mode 0, the 8-bit address / 8-bit command variant in general
    consumer use, is supported. The longer-address RC-6A modes are a
    separate protocol and are not encoded here.
    """

    address: int
    command: int
    toggle: int

    def __init__(
        self,
        *,
        address: int,
        command: int,
        toggle: int = 0,
        modulation: int = RC6_MODULATION_HZ,
        repeat_count: int = 0,
    ) -> None:
        """Initialize the RC-6 IR command."""
        if not 0 <= address <= 0xFF:
            raise ValueError("RC-6 address must be in range 0x00..0xFF")
        if not 0 <= command <= 0xFF:
            raise ValueError("RC-6 command must be in range 0x00..0xFF")
        super().__init__(modulation=modulation, repeat_count=repeat_count)
        self.address = address
        self.command = command
        self.toggle = toggle

    @override
    def get_raw_timings(self) -> list[int]:
        """Get raw timings for the RC-6 command.

        RC-6 mode 0 protocol timing (in microseconds):
        - Carrier: 36 kHz
        - Unit time: 444µs; normal bit 888µs, trailer bit 1776µs
        - Leader: 2664µs burst, 888µs space
        - Frame: start bit (always 1), 3 mode bits (000 for mode 0),
          trailer bit carrying the toggle, address (8 bits, MSB first),
          command (8 bits, MSB first)
        - Logical '1': burst in first half of bit time (high then low)
        - Logical '0': burst in second half of bit time (low then high)
        - Total frame duration: 23088µs
        - Signal-free time: at least 2664µs before the next frame may start
        - Repeat period: 107ms (key still pressed)

        The trailer bit is twice as wide as a normal bit, which is what
        distinguishes it in a captured frame.
        """
        frame: list[int] = [RC6_LEADER_MARK_US, -RC6_LEADER_SPACE_US]

        manchester_encode_bit(frame, 1, RC6_UNIT_US)
        for mode_bit in RC6_MODE_0_BITS:
            manchester_encode_bit(frame, mode_bit, RC6_UNIT_US)

        manchester_encode_bit(frame, self.toggle & 1, 2 * RC6_UNIT_US)

        for i in range(7, -1, -1):
            manchester_encode_bit(frame, (self.address >> i) & 1, RC6_UNIT_US)
        for i in range(7, -1, -1):
            manchester_encode_bit(frame, (self.command >> i) & 1, RC6_UNIT_US)

        # A frame ending on logic '1' closes with a space half-bit, which is
        # indistinguishable from the signal-free time that follows it. Drop it
        # to keep a pulse-bracketed timing list.
        if frame[-1] < 0:
            frame.pop()

        timings = list(frame)

        # Repeats are the same frame retransmitted every 107ms while the key
        # remains pressed. The toggle bit only flips between distinct key
        # presses, so it stays constant across repeats.
        if self.repeat_count > 0:
            frame_duration = sum(abs(t) for t in frame)
            gap = RC6_REPEAT_PERIOD_US - frame_duration
            for _ in range(self.repeat_count):
                timings.append(-gap)
                timings.extend(frame)

        return timings

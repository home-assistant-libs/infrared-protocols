"""RC-5 IR command (Philips, Marantz, and other devices)."""

from typing import override

from . import Command

# RC-5 timing unit (half-bit) in microseconds. The full bit period is 2 × this.
RC5_HALF_BIT_US = 889
# RC-5 carrier frequency in Hz.
RC5_MODULATION_HZ = 36000
# Time between the start of one frame and the start of the next while a key is
# held. A standard 14-bit RC-5 frame fits inside this with idle space to spare.
RC5_REPEAT_PERIOD_US = 114000


def append_signed_us(timings: list[int], value: int) -> None:
    """Append a microsecond duration, merging into the last entry if same sign."""
    if timings and (timings[-1] > 0) == (value > 0):
        timings[-1] += value
    else:
        timings.append(value)


def manchester_encode_bit(timings: list[int], bit: int, half_bit_us: int) -> None:
    """Append the two Manchester half-bits for ``bit`` to ``timings``.

    Logic '0' is a burst followed by a space; logic '1' is a space followed
    by a burst. Adjacent halves of equal sign are merged.
    """
    if bit:
        append_signed_us(timings, -half_bit_us)
        append_signed_us(timings, half_bit_us)
    else:
        append_signed_us(timings, half_bit_us)
        append_signed_us(timings, -half_bit_us)


def strip_idle_edges(timings: list[int]) -> None:
    """Drop any leading and trailing space (negative) entries in place.

    Manchester-encoded frames include an idle space before the first burst
    (when the leading bit's first half is space) and may end on a space.
    Neither carries information, so we strip them to keep a clean
    pulse-bracketed timing list.
    """
    if timings and timings[0] < 0:
        timings.pop(0)
    if timings and timings[-1] < 0:
        timings.pop()


class RC5Command(Command):
    """RC-5 IR command (Philips, Marantz amplifiers, and similar devices).

    This is the protocol used by Marantz integrated amplifiers such as the
    PM6006, by Philips consumer electronics, and by many other devices that
    adopted the Philips RC-5 standard.

    Both standard RC-5 (5-bit address, 6-bit command) and the extended
    RC-5 / RC5X variant (5-bit address, 7-bit command) are supported.
    A ``command`` with bit 6 set automatically selects the extended
    encoding (with the second start bit re-purposed as the inverted MSB
    of the command).
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
        modulation: int = RC5_MODULATION_HZ,
        repeat_count: int = 0,
    ) -> None:
        """Initialize the RC-5 IR command."""
        if not 0 <= address <= 0x1F:
            raise ValueError("RC-5 address must be in range 0x00..0x1F")
        if not 0 <= command <= 0x7F:
            raise ValueError("RC-5 command must be in range 0x00..0x7F")
        super().__init__(modulation=modulation, repeat_count=repeat_count)
        self.address = address
        self.command = command
        self.toggle = toggle

    @override
    def get_raw_timings(self) -> list[int]:
        """Get raw timings for the RC-5 command.

        RC-5 protocol timing (in microseconds):
        - Carrier: 36 kHz
        - Bit time: 1778µs (half-bit: 889µs)
        - Frame: 14 bits, Manchester encoded
          (S1, S2, T, A4..A0 MSB first, C5..C0 MSB first)
        - Logical '0': burst in first half of bit time (high then low)
        - Logical '1': burst in second half of bit time (low then high)
        - Total frame duration: ~25ms
        - Repeat period: 114ms (key still pressed)

        For extended RC-5 (command bit 6 set) the second start bit
        ``S2`` is replaced by the inverted MSB of the 7-bit command,
        providing a 7-bit command field.
        """
        # S2 is the inverted MSB (bit 6) of the 7-bit command. For
        # standard RC-5 (bit 6 clear) this is 1, the original idle-frame
        # marker; for RC5X commands (bit 6 set) it is 0.
        start_bit_2 = 0 if self.command & 0x40 else 1
        command_bits = self.command & 0x3F

        # Build the 14-bit frame: S1, S2, T, address (MSB first),
        # command (MSB first).
        bits: list[int] = [1, start_bit_2, self.toggle & 1]
        for i in range(4, -1, -1):
            bits.append((self.address >> i) & 1)
        for i in range(5, -1, -1):
            bits.append((command_bits >> i) & 1)

        frame: list[int] = []
        for bit in bits:
            manchester_encode_bit(frame, bit, RC5_HALF_BIT_US)
        strip_idle_edges(frame)

        timings = list(frame)

        # Repeats are the same frame retransmitted every 114ms while the
        # key remains pressed. The toggle bit only flips between distinct
        # key presses, so it stays constant across repeats.
        if self.repeat_count > 0:
            frame_duration = sum(abs(t) for t in frame)
            gap = RC5_REPEAT_PERIOD_US - frame_duration
            for _ in range(self.repeat_count):
                timings.append(-gap)
                timings.extend(frame)

        return timings

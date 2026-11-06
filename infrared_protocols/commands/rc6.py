"""RC-6 IR command (Philips, Microsoft MCE, and other devices)."""

from typing import Self, override

from . import Command
from ._decode import frames, levels, manchester
from ._timing import Reader, number

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
    """RC-6 with an 8-bit address and 8-bit command.

    Mode defaults to 0. The three-bit mode field can be selected explicitly,
    matching ESPHome's fixed-width transport. Longer RC-6A payloads are not
    supported by this class.
    """

    address: int
    command: int
    toggle: int
    mode: int

    def __init__(
        self,
        *,
        address: int,
        command: int,
        toggle: int = 0,
        mode: int = 0,
        modulation: int = RC6_MODULATION_HZ,
        repeat_count: int = 0,
    ) -> None:
        """Initialize the RC-6 IR command."""
        if not 0 <= address <= 0xFF:
            raise ValueError("RC-6 address must be in range 0x00..0xFF")
        if not 0 <= command <= 0xFF:
            raise ValueError("RC-6 command must be in range 0x00..0xFF")
        if not 0 <= mode <= 7:
            raise ValueError("RC-6 mode must fit in three bits")
        super().__init__(modulation=modulation, repeat_count=repeat_count)
        self.address = address
        self.command = command
        self.toggle = toggle
        self.mode = mode

    @override
    def get_raw_timings(self) -> list[int]:
        """Get raw timings for the RC-6 command.

        RC-6 protocol timing (in microseconds):
        - Carrier: 36 kHz
        - Unit time: 444µs; normal bit 888µs, trailer bit 1776µs
        - Leader: 2664µs burst, 888µs space
        - Frame: start bit (always 1), 3 configurable mode bits (0..7),
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
        for mode_bit in ((self.mode >> i) & 1 for i in range(2, -1, -1)):
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

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode the 8-bit address/command layout with a double-width toggle cell."""
        messages: list[tuple[int, int, int, int]] = []
        try:
            for frame in frames(timings, period=RC6_REPEAT_PERIOD_US):
                reader = Reader(timings=frame)
                reader.expect(RC6_LEADER_MARK_US, -RC6_LEADER_SPACE_US)
                values = levels(frame[2:], RC6_UNIT_US)
                if len(values) == 43:
                    values.append(0)
                if len(values) != 44 or values[8:12] not in (
                    [0, 0, 1, 1],
                    [1, 1, 0, 0],
                ):
                    return None
                header = manchester(values[:8], one_starts_high=True)
                payload = manchester(values[12:], one_starts_high=True)
                if header[0] != 1:
                    return None
                messages.append(
                    (
                        number(header[1:]),
                        values[8],
                        number(payload[:8]),
                        number(payload[8:]),
                    )
                )
            first = messages[0]
            if any(message != first for message in messages[1:]):
                return None
            return cls(
                mode=first[0],
                toggle=first[1],
                address=first[2],
                command=first[3],
                repeat_count=len(messages) - 1,
            )
        except ValueError:
            return None

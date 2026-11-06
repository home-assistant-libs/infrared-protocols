"""Kaseikyo format IR command."""

from collections.abc import Callable
from typing import Self, override

from . import Command
from ._timing import PulseTiming, Reader, close, pack_bytes


class KaseikyoCommand(Command):
    """Kaseikyo format IR command."""

    address: int
    data: bytes | list[bytes]
    error_correction: Callable[[bytes], bytes] | None
    base_unit: float

    def __init__(
        self,
        *,
        address: int,
        data: bytes | list[bytes],
        error_correction: Callable[[bytes], bytes] | None = None,
        modulation: int = 38000,
        burst_pulse: int = 16,
        repeat_count: int = 0,
        full_frame_repeat: bool = False,
    ) -> None:
        """Initialize the Kaseikyo IR command.

        ``data`` is the payload following the 16-bit address. Pass a single
        ``bytes`` for a single-frame command, or a ``list[bytes]`` to send
        several frames (each sharing the same address) as one multi-frame
        message separated by an inter-frame gap.

        Full-frame repeats require a single section; repeating section groups
        cannot always be distinguished from additional application sections.
        """
        if full_frame_repeat and isinstance(data, list) and len(data) > 1:
            raise ValueError("full_frame_repeat only supports a single payload section")
        super().__init__(modulation=modulation, repeat_count=repeat_count)
        self.full_frame_repeat = full_frame_repeat
        self._frame_gaps: list[int] = []
        self._repeat_gaps: list[int] = []
        self.address = address
        self.data = data
        self.error_correction = error_correction
        self.base_unit = 1000000 * burst_pulse / modulation

    @override
    def get_raw_timings(self) -> list[int]:
        """Get raw timings for the Kaseikyo command.

        Kaseikyo protocol timing (in base time units):
        - T: base time unit (350µs - 500µs, 16/38kHz = 421µs typ.)
        - Leader pulse: 8T high, 4T low
        - Logical '0': 1T high, 1T low
        - Logical '1': 1T high, 3T low
        - End pulse: 1T high
        - Repeat code: 8T high, 8T low, 1T end pulse
        - Frame gap: total frame typically ~130ms

        Data format (variable length, LSB first):
        - Address (16-bit) + Parity (4-bit) + Data 0 (4-bit) + Data 1 (8-bit) + ...
        """
        leader_high = round(8 * self.base_unit)
        leader_low = round(4 * self.base_unit)
        repeat_low = round(8 * self.base_unit)
        bit_high = round(1 * self.base_unit)
        zero_low = round(1 * self.base_unit)
        one_low = round(3 * self.base_unit)
        frame_time = 130000
        trailer_min = 8000
        multi_frame_gap = 10000
        repeat_frame_gap = max(
            frame_time - (leader_high + repeat_low + bit_high), trailer_min
        )

        parity = self.address & 0xFFFF
        parity ^= parity >> 8
        parity ^= parity >> 4
        parity &= 0x0F

        frames = [self.data] if isinstance(self.data, bytes) else self.data

        timings: list[int] = []
        for i, frame in enumerate(frames):
            if i != 0:
                # Inter-frame gap for multi-frame commands
                timings.append(
                    -(self._frame_gaps[i - 1] if self._frame_gaps else multi_frame_gap)
                )
            timings.extend([leader_high, -leader_low])

            data_bytes = [
                self.address & 0xFF,
                (self.address >> 8) & 0xFF,
                (frame[0] & 0xF0) | parity,
                *frame[1:],
            ]
            if self.error_correction:
                data_bytes.extend(self.error_correction(bytes(data_bytes)))

            for byte in data_bytes:
                for _ in range(8):
                    bit = byte & 1
                    timings.append(bit_high)
                    timings.append(-one_low if bit else -zero_low)
                    byte >>= 1

            # End pulse
            timings.append(bit_high)

        # Add repeat codes if requested
        gap = max(frame_time - sum(abs(t) for t in timings), trailer_min)
        if self.full_frame_repeat:
            frame = timings.copy()
            for index in range(self.repeat_count):
                repeat_gap = (
                    self._repeat_gaps[index] if index < len(self._repeat_gaps) else gap
                )
                timings.extend([-repeat_gap, *frame])
            return timings
        for _ in range(self.repeat_count):
            timings.extend([-gap, leader_high, -repeat_low, bit_high])
            gap = repeat_frame_gap  # Use standard frame gap for subsequent repeats

        return timings

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode address/parity, complete byte frames and trailing repeat codes.

        Application checksums remain in data for the device-specific decoder.
        Carrier frequency cannot be recovered from demodulated pulse timings.
        """
        if len(timings) < 2 or not 2600 <= timings[0] <= 4400:
            return None
        unit = round((timings[0] - timings[1]) / 12)
        reader = Reader(timings=timings)
        address: int | None = None
        payloads: list[bytes] = []
        repeats = 0
        gaps: list[int] = []
        starts: list[int] = []
        try:
            while reader.pos < len(timings):
                if payloads:
                    if len(timings) - reader.pos == 1:
                        reader.end()
                        break
                    if timings[reader.pos] > -3000:
                        raise ValueError("missing Kaseikyo frame gap")
                    gaps.append(-timings[reader.pos])
                    reader.pos += 1
                start = reader.pos
                reader.expect(8 * unit)
                if reader.pos < len(timings) and close(timings[reader.pos], -8 * unit):
                    reader.expect(-8 * unit, unit)
                    if not payloads:
                        raise ValueError("standalone repeat has no command")
                    repeats += 1
                    continue
                if repeats:
                    raise ValueError("data after a Kaseikyo repeat")
                reader.expect(-4 * unit)
                values: list[int] = []
                while (
                    reader.pos + 1 < len(timings)
                    and timings[reader.pos + 1] > -5 * unit
                ):
                    values.extend(
                        reader.read_bits(PulseTiming(unit, unit, 3 * unit), 1)
                    )
                reader.expect(unit)
                data = pack_bytes(values)
                if len(data) < 3:
                    raise ValueError("Kaseikyo needs address and parity bytes")
                frame_address = data[0] | data[1] << 8
                parity = data[0] ^ data[1] ^ data[0] >> 4 ^ data[1] >> 4
                if (
                    data[2] & 15 != parity & 15
                    or address is not None
                    and frame_address != address
                ):
                    raise ValueError("invalid Kaseikyo address or parity")
                address = frame_address
                payloads.append(bytes([data[2] & 0xF0]) + data[3:])
                starts.append(start)
            if address is None or not payloads:
                return None
            clock_scale = (timings[0] - timings[1]) / 12 / (16000000 / 38000)
            full_repeat = (
                len(payloads) > 1
                and all(value == payloads[0] for value in payloads)
                # A normal section gap stays a section even for identical payloads.
                and all(gap > 12500 * clock_scale for gap in gaps)
                and all(
                    close(
                        sum(abs(t) for t in timings[a:b]),
                        130000 * clock_scale,
                        tolerance=0.05,
                    )
                    for a, b in zip(starts, starts[1:], strict=False)
                )
            )
            if full_repeat:
                if repeats:
                    return None
                repeats = len(payloads) - 1
                payloads = payloads[:1]
            result = cls(
                address=address,
                data=payloads[0] if len(payloads) == 1 else payloads,
                repeat_count=repeats,
                full_frame_repeat=full_repeat,
            )
            result.base_unit = (timings[0] - timings[1]) / 12
            result._frame_gaps = gaps[: len(payloads) - 1]
            result._repeat_gaps = gaps if full_repeat else []
            return result
        except ValueError:
            return None

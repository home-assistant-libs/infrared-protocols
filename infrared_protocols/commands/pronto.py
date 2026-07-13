"""Pronto IR command code format."""

import struct
from textwrap import wrap
from typing import Self, override

from . import Command

PRONTO_PREAMBLE_LEARNED_TOKEN = b"\x00\x00"
# To get the unit pulse length in microseconds,
# divide 1000 * 1000 (microseconds per second) by reference frequency
PRONTO_REFERENCE_FREQUENCY = 4145146
PRONTO_DEFAULT_FREQUENCY = 38000


class ProntoCommand(Command):
    """Pronto IR command.

    A pronto code consists of a 4 word preamble and timing data.
    A data word of pronto is 2 bytes long.
    Two data words (4 bytes) encode one content bit.
    The preamble consists of:
    1 word indicating the token source (currently supported: learned).
    1 word indicating the modulation frequency.
    1 word indicating the length of the timing data in content bits.
    1 word indicating the amount of repeats of the timing data.
    After the preamble, the timing data follows in pairs of two words
    (mark and space duration).

    Most of the code has been ported from the ESPHome sources at
    https://github.com/esphome/esphome/blob/dev/esphome/components/remote_base/pronto_protocol.cpp.
    """

    timing_data: bytes

    def __init__(
        self,
        *,
        timing_data: bytes,
        modulation: int = PRONTO_DEFAULT_FREQUENCY,
        repeat_count: int = 0,
    ) -> None:
        """Initialize the Pronto IR command."""
        super().__init__(modulation=modulation, repeat_count=repeat_count)
        self.timing_data = timing_data

    def __repr__(self) -> str:
        """Get string representation for this pronto code."""
        content_bytes_hex = b"".join(
            [
                PRONTO_PREAMBLE_LEARNED_TOKEN,
                ProntoCommand._int_to_pronto(
                    value=round(PRONTO_REFERENCE_FREQUENCY / self.modulation)
                ),  # Modulation
                ProntoCommand._int_to_pronto(
                    value=int(len(self.timing_data) / 4)
                ),  # in content bits
                ProntoCommand._int_to_pronto(value=self.repeat_count),  # repeats
                self.timing_data,
            ]
        ).hex()
        return " ".join(wrap(content_bytes_hex, 4))

    @staticmethod
    def _int_to_pronto(value: int) -> bytes:
        return struct.pack(">h", value)

    @staticmethod
    def _pronto_to_int(pronto_block: bytes) -> int:
        return struct.unpack(">h", pronto_block)[0]

    @staticmethod
    def _time_base(modulation: int) -> float:
        """Calculate base pulse length in microseconds for a given modulation."""
        return 1000000 / modulation

    @staticmethod
    def _compensate_duration(value: int, time_base: float) -> int:
        """Compensate positive/negative durations to positive ones."""
        if value > 0:
            result = value - 20
        else:
            result = -value + 20
        return round((result + time_base / 2) / time_base)

    @override
    def get_raw_timings(self) -> list[int]:
        """Get raw timings for the Pronto command.

        Durations are encoded in the pronto timing data and only need to be converted.
        """
        time_base = ProntoCommand._time_base(self.modulation)
        return [
            symbol
            for value in zip(
                self.timing_data[::4],
                self.timing_data[1::4],
                self.timing_data[2::4],
                self.timing_data[3::4],
                strict=True,
            )
            for symbol in (
                # mark
                min(
                    round(
                        ProntoCommand._pronto_to_int(pronto_block=bytes(value[:2]))
                        * time_base
                    ),
                    0xFFFF,
                ),
                # space
                -min(
                    round(
                        ProntoCommand._pronto_to_int(pronto_block=bytes(value[2:]))
                        * time_base
                    ),
                    0xFFFF,
                ),
            )
        ] * (self.repeat_count + 1)

    @classmethod
    def from_raw_timings(
        cls, timings: list[int], modulation: int | None = None
    ) -> Self:
        """Decode raw IR timings into a ProntoCommand.

        If modulation is None, the typical 38000 kHz are used.
        Returns a ProntoCommand.
        """
        if modulation is None:
            modulation = PRONTO_DEFAULT_FREQUENCY
        time_base = ProntoCommand._time_base(modulation=modulation)
        timing_data = b"".join(
            ProntoCommand._int_to_pronto(
                value=ProntoCommand._compensate_duration(
                    value=timing, time_base=time_base
                )
            )
            for timing in timings
        )
        return cls(
            timing_data=timing_data,
            modulation=modulation,
            repeat_count=0,
        )

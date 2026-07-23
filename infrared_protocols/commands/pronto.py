"""Pronto IR command code format."""

import string
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
    Two data words (4 bytes) encode one burst pair.
    The preamble consists of:
    1 word indicating the token source (currently supported: learned).
    1 word indicating the modulation frequency.
    1 word indicating the number of burst pairs in the once sequence.
    1 word indicating the number of burst pairs in the repeat sequence.
    After the preamble, the timing data follows in pairs of two words
    (mark and space duration).

    The modulation frequency is always derived from the preamble. Repetition
    is represented by the code's own repeat sequence: get_raw_timings emits
    the once sequence followed by repeat_count passes of the repeat sequence.
    For a code without a once sequence, the repeat sequence is emitted
    repeat_count + 1 times.

    Most of the code has been ported from the ESPHome sources at
    https://github.com/esphome/esphome/blob/dev/esphome/components/remote_base/pronto_protocol.cpp.
    """

    pronto_data: bytes

    def __init__(self, *, pronto_data: bytes, repeat_count: int = 0) -> None:
        """Initialize the Pronto IR command from a full pronto code.

        The code must contain the 4 word preamble followed by the timing data
        of the once and repeat sequences. repeat_count controls how many
        passes of the code's repeat sequence are emitted after the initial
        transmission.
        """
        words = ProntoCommand._unpack_words(pronto_data=pronto_data)
        if len(words) < 4:
            raise ValueError("pronto code must start with a 4 word preamble")
        if pronto_data[:2] != PRONTO_PREAMBLE_LEARNED_TOKEN:
            raise ValueError("only learned pronto codes (token 0000) are supported")

        frequency_word, once_pairs, repeat_pairs = words[1:4]
        if frequency_word == 0:
            raise ValueError("pronto frequency word must not be zero")

        timing_words = words[4:]
        if len(timing_words) != (once_pairs + repeat_pairs) * 2:
            raise ValueError(
                "pronto timing data does not match the preamble burst pair counts"
            )
        if not timing_words:
            raise ValueError("pronto code must contain at least one burst pair")
        if any(word == 0 for word in timing_words):
            raise ValueError("pronto timing words must not be zero")
        if repeat_count > 0 and repeat_pairs == 0:
            raise ValueError("pronto code has no repeat sequence to repeat")

        super().__init__(
            modulation=round(PRONTO_REFERENCE_FREQUENCY / frequency_word),
            repeat_count=repeat_count,
        )
        self.pronto_data = pronto_data

    def to_pronto_hex(self) -> str:
        """Serialize this command to a space-separated pronto hex string."""
        return " ".join(wrap(self.pronto_data.hex(), 4))

    def __repr__(self) -> str:
        """Get string representation for this pronto code."""
        return self.to_pronto_hex()

    @staticmethod
    def _int_to_pronto(value: int) -> bytes:
        return struct.pack(">H", value)

    @staticmethod
    def _unpack_words(*, pronto_data: bytes) -> tuple[int, ...]:
        if len(pronto_data) % 2:
            raise ValueError("pronto data must consist of 2 byte words")
        return struct.unpack(f">{len(pronto_data) // 2}H", pronto_data)

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

        The once sequence is emitted first, followed by repeat_count passes of
        the repeat sequence. For a code without a once sequence, the repeat
        sequence is emitted repeat_count + 1 times.
        """
        words = ProntoCommand._unpack_words(pronto_data=self.pronto_data)
        once_word_count = words[2] * 2
        once_timings = ProntoCommand._words_to_timings(
            timing_words=words[4 : 4 + once_word_count], modulation=self.modulation
        )
        repeat_timings = ProntoCommand._words_to_timings(
            timing_words=words[4 + once_word_count :], modulation=self.modulation
        )
        return (once_timings or repeat_timings) + repeat_timings * self.repeat_count

    @staticmethod
    def _words_to_timings(
        *, timing_words: tuple[int, ...], modulation: int
    ) -> list[int]:
        """Convert pronto timing words to raw timings."""
        time_base = ProntoCommand._time_base(modulation=modulation)
        return [
            symbol
            for mark, space in zip(timing_words[::2], timing_words[1::2], strict=True)
            for symbol in (
                min(round(mark * time_base), 0xFFFF),
                -min(round(space * time_base), 0xFFFF),
            )
        ]

    @classmethod
    def from_raw_timings(
        cls, timings: list[int], modulation: int | None = None
    ) -> Self:
        """Convert raw timings to ProntoCommand.

        If modulation is None, the typical 38000 Hz are used. All timings are
        encoded as the once sequence.
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
            pronto_data=b"".join(
                [
                    PRONTO_PREAMBLE_LEARNED_TOKEN,
                    ProntoCommand._int_to_pronto(
                        value=round(PRONTO_REFERENCE_FREQUENCY / modulation)
                    ),  # modulation frequency
                    ProntoCommand._int_to_pronto(
                        value=len(timings) // 2
                    ),  # once sequence burst pairs
                    ProntoCommand._int_to_pronto(
                        value=0
                    ),  # repeat sequence burst pairs
                    timing_data,
                ]
            )
        )

    @classmethod
    def from_pronto_hex(cls, pronto_hex: str, *, repeat_count: int = 0) -> Self:
        """Decode a full pronto hex string into a ProntoCommand.

        Returns a ProntoCommand.
        """
        words = pronto_hex.split()
        for word in words:
            if len(word) != 4 or any(char not in string.hexdigits for char in word):
                raise ValueError(f"pronto words must be 4 hex digits, got {word!r}")
        return cls(pronto_data=bytes.fromhex("".join(words)), repeat_count=repeat_count)

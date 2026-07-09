"""Pronto HEX command support.

Public API:
- ProntoCommand: Command implementation for learned/raw Pronto HEX type 0000.
- ProntoCommand(pronto_hex=...): create a command from complete Pronto HEX.
- ProntoCommand.from_raw_timings(...): create a command from signed raw timings.
- decode_pronto_hex(...): decode Pronto HEX into modulation and signed timings.
- encode_pronto_hex(...): encode signed raw timings as Pronto HEX.
- ProntoCode: decoded modulation and signed timing data.
- ProntoError: raised for malformed or unsupported Pronto data.

Only learned/raw Pronto HEX type 0000 is supported. Public timings use the
infrared-protocols signed convention: positive values are marks, negative values
are spaces, and durations are in microseconds.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Self

from . import Command

__all__ = [
    "ProntoCode",
    "ProntoCommand",
    "ProntoError",
    "decode_pronto_hex",
    "encode_pronto_hex",
]

_PRONTO_TYPE_LEARNED_RAW = 0x0000
_PRONTO_FREQUENCY_REFERENCE_US = 0.241246
_PRONTO_HEADER_WORD_COUNT = 4
_PRONTO_MAX_WORD = 0xFFFF

_DEFAULT_MODULATION = 38_000
_DEFAULT_TRAILING_GAP_US = 100_000


@dataclass(frozen=True, slots=True)
class ProntoCode:
    """Decoded Pronto modulation and signed timing data."""

    modulation: int
    timings: tuple[int, ...]


class ProntoError(ValueError):
    """Raised when Pronto data cannot be parsed or generated."""


class ProntoCommand(Command):
    """Command implementation for learned/raw Pronto HEX type 0000."""

    def __init__(
        self,
        *,
        pronto_hex: str,
        repeat_count: int = 0,
    ) -> None:
        """Initialize a command from complete Pronto HEX."""
        decoded = decode_pronto_hex(pronto_hex)
        super().__init__(
            modulation=decoded.modulation,
            repeat_count=repeat_count,
        )
        self._timings = decoded.timings
        self._pronto_hex = _normalize_pronto_hex(pronto_hex)

    @classmethod
    def from_raw_timings(
        cls,
        timings: Iterable[int],
        modulation: int = _DEFAULT_MODULATION,
        *,
        repeat_count: int = 0,
        trailing_gap_us: int | None = _DEFAULT_TRAILING_GAP_US,
    ) -> Self:
        """Create a command from signed raw timings."""
        return cls(
            pronto_hex=encode_pronto_hex(
                timings,
                modulation,
                trailing_gap_us=trailing_gap_us,
            ),
            repeat_count=repeat_count,
        )

    def get_raw_timings(self) -> list[int]:
        """Return signed raw timings for this command."""
        return list(self._timings) * (self.repeat_count + 1)

    def to_pronto_hex(self) -> str:
        """Return normalized learned/raw Pronto HEX."""
        return self._pronto_hex

    def __str__(self) -> str:
        """Return normalized learned/raw Pronto HEX."""
        return self.to_pronto_hex()


def decode_pronto_hex(pronto_hex: str) -> ProntoCode:
    """Decode learned/raw Pronto HEX type 0000."""
    words = _parse_pronto_words(pronto_hex)

    if len(words) < _PRONTO_HEADER_WORD_COUNT:
        raise ProntoError("Pronto HEX is too short")

    pronto_type, frequency_word, intro_pairs, repeat_pairs = words[:4]

    if pronto_type != _PRONTO_TYPE_LEARNED_RAW:
        raise ProntoError("Only learned/raw Pronto HEX type 0000 is supported")

    if frequency_word <= 0:
        raise ProntoError("Pronto frequency word must be greater than zero")

    pair_count = intro_pairs + repeat_pairs
    if pair_count <= 0:
        raise ProntoError("Pronto HEX must contain at least one timing pair")

    timing_words = words[_PRONTO_HEADER_WORD_COUNT:]
    expected_timing_word_count = pair_count * 2

    if len(timing_words) != expected_timing_word_count:
        raise ProntoError("Pronto timing word count does not match header")

    if any(word <= 0 for word in timing_words):
        raise ProntoError("Pronto timing words must be greater than zero")

    modulation = round(1_000_000 / (frequency_word * _PRONTO_FREQUENCY_REFERENCE_US))
    timings = tuple(
        _apply_timing_sign(index, _pronto_word_to_microseconds(word, frequency_word))
        for index, word in enumerate(timing_words)
    )

    return ProntoCode(modulation=modulation, timings=timings)


def _parse_pronto_words(pronto_hex: str) -> list[int]:
    """Parse Pronto HEX words."""
    if not pronto_hex.strip():
        raise ProntoError("Pronto HEX cannot be empty")

    words: list[int] = []

    for word in pronto_hex.split():
        if len(word) != 4 or any(
            character not in "0123456789abcdefABCDEF" for character in word
        ):
            raise ProntoError("Pronto HEX words must contain four hex digits")

        words.append(int(word, 16))

    return words


def _normalize_pronto_hex(pronto_hex: str) -> str:
    """Return normalized uppercase Pronto HEX."""
    return " ".join(f"{word:04X}" for word in _parse_pronto_words(pronto_hex))


def _pronto_word_to_microseconds(word: int, frequency_word: int) -> int:
    """Convert a Pronto timing word to microseconds."""
    return round(word * frequency_word * _PRONTO_FREQUENCY_REFERENCE_US)


def _apply_timing_sign(index: int, timing: int) -> int:
    """Apply signed mark/space timing convention."""
    return timing if index % 2 == 0 else -timing


def encode_pronto_hex(
    timings: Iterable[int],
    modulation: int,
    *,
    trailing_gap_us: int | None = _DEFAULT_TRAILING_GAP_US,
) -> str:
    """Encode signed raw timings as learned/raw Pronto HEX type 0000."""
    frequency_word = _modulation_to_frequency_word(modulation)
    timing_durations = _normalize_encode_timings(timings, trailing_gap_us)

    pair_count = len(timing_durations) // 2
    if pair_count > _PRONTO_MAX_WORD:
        raise ProntoError("Pronto timing pair count exceeds 16-bit value")

    timing_words = [
        _microseconds_to_pronto_word(duration, frequency_word)
        for duration in timing_durations
    ]

    words = [
        _PRONTO_TYPE_LEARNED_RAW,
        frequency_word,
        pair_count,
        0x0000,
        *timing_words,
    ]

    return " ".join(f"{word:04X}" for word in words)


def _modulation_to_frequency_word(modulation: int) -> int:
    """Convert modulation frequency to a Pronto frequency word."""
    if type(modulation) is not int or modulation <= 0:
        raise ProntoError("modulation must be a positive integer")

    frequency_word = round(1_000_000 / (modulation * _PRONTO_FREQUENCY_REFERENCE_US))

    if frequency_word <= 0:
        raise ProntoError("Pronto frequency word must be greater than zero")

    if frequency_word > _PRONTO_MAX_WORD:
        raise ProntoError("Pronto frequency word exceeds 16-bit value")

    return frequency_word


def _normalize_encode_timings(
    timings: Iterable[int],
    trailing_gap_us: int | None,
) -> list[int]:
    """Normalize raw timings for Pronto encoding."""
    timing_durations = [_normalize_duration(timing) for timing in timings]

    if not timing_durations:
        raise ProntoError("timings cannot be empty")

    if len(timing_durations) % 2:
        if trailing_gap_us is None:
            raise ProntoError("timings must contain mark/space pairs")

        timing_durations.append(_normalize_duration(-trailing_gap_us))

    return timing_durations


def _normalize_duration(timing: int) -> int:
    """Normalize a signed timing to an unsigned Pronto duration."""
    if type(timing) is not int:
        raise ProntoError("timings must be integers")

    if timing == 0:
        raise ProntoError("timings must be non-zero")

    return abs(timing)


def _microseconds_to_pronto_word(duration: int, frequency_word: int) -> int:
    """Convert microseconds to a Pronto timing word."""
    word = round(duration / (frequency_word * _PRONTO_FREQUENCY_REFERENCE_US))

    if word <= 0:
        raise ProntoError("Pronto timing word must be greater than zero")

    if word > _PRONTO_MAX_WORD:
        raise ProntoError("Pronto timing word exceeds 16-bit value")

    return word

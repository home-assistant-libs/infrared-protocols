"""Commands for Dyson infrared protocol."""

from typing import ClassVar, Self, override

from . import Command
from ._timing import PulseTiming, Reader, bits, number


class _DysonPacketCommand(Command):
    """The shared 15-bit payload used by all Dyson fan remotes."""

    HEADER: ClassVar[tuple[int, int]] = (2440, -870)
    TIMING: ClassVar[PulseTiming] = PulseTiming(850, 850, 1660)
    payload: int

    @property
    def button_code(self) -> int:
        """Return the common 13-bit button identifier, excluding the index."""
        return self.payload >> 2

    @property
    def index(self) -> int:
        """Return the two-bit rolling index, including for legacy button tables."""
        return self.payload & 3

    @override
    def get_raw_timings(self) -> list[int]:
        """Encode the shared payload with this remote's nominal timings."""
        return [
            *self.HEADER,
            *self.TIMING.encode(bits(self.payload, 15)),
            self.TIMING.mark,
        ]

    @classmethod
    def _read_payload(cls, timings: list[int]) -> int | None:
        reader = Reader(timings=timings)
        try:
            reader.expect(*cls.HEADER)
            value = number(reader.read_bits(cls.TIMING, 15))
            reader.expect(cls.TIMING.mark)
            reader.end()
            return value
        except ValueError:
            return None


class _DysonFanCommand(_DysonPacketCommand):
    """Compatibility API: an eight-bit code with a fixed family prefix.

    These commands share DysonCommand's transport. Use button_code and index
    for the same 13+2-bit interpretation; code retains the existing API.
    """

    _PREAMBLE: ClassVar[int]

    def __init__(self, *, code: int, modulation: int = 38000) -> None:
        """Initialize the existing family-prefixed command."""
        if not 0 <= code <= 0xFF:
            raise ValueError("Dyson command code must be a valid 8-bit value")
        super().__init__(modulation=modulation)
        self.payload = self._PREAMBLE << 8 | code

    @property
    def code(self) -> int:
        """Return the family-prefixed eight-bit button code."""
        return self.payload & 255

    @code.setter
    def code(self, value: int) -> None:
        bits(value, 8)
        self.payload = self._PREAMBLE << 8 | value

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode the common transport and validate the family prefix."""
        value = cls._read_payload(timings)
        return (
            cls(code=value & 255)
            if value is not None and value >> 8 == cls._PREAMBLE
            else None
        )


class DysonCoolCommand(_DysonFanCommand):
    """Dyson Cool infrared command."""

    _PREAMBLE = 0b1001000


class DysonAm09Command(_DysonFanCommand):
    """Dyson AM09 (Hot+Cool) infrared command."""

    _PREAMBLE = 0b0011000


class DysonCommand(_DysonPacketCommand):
    """The same Dyson transport with an explicit button and rolling index.

    Family-prefixed commands also decode here. Protocol dispatch should select
    the configured family; these are payload views, not distinct protocols.
    """

    HEADER = (2280, -720)
    TIMING = PulseTiming(780, 720, 1500)

    def __init__(self, *, code: int, index: int = 0, modulation: int = 36000) -> None:
        """Build a 13-bit button identifier and two-bit rolling index."""
        bits(code, 13)
        bits(index, 2)
        super().__init__(modulation=modulation)
        self.payload = code << 2 | index

    @property
    def code(self) -> int:
        """Return the button identifier without the rolling index."""
        return self.button_code

    @code.setter
    def code(self, value: int) -> None:
        bits(value, 13)
        self.payload = value << 2 | self.index

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode the shared 15-bit packet without a family-prefix constraint."""
        value = cls._read_payload(timings)
        return cls(code=value >> 2, index=value & 3) if value is not None else None

"""CanalSat and CanalSatLD biphase infrared commands."""

from typing import ClassVar, Self, override

from . import Command
from ._decode import levels as decode_levels
from ._timing import bits, close, number, runs


class CanalSatCommand(Command):
    """CanalSat receiver address and button, including the received repeat flag."""

    UNIT: ClassVar[int] = 250
    CARRIER: ClassVar[int] = 55500

    def __init__(
        self,
        *,
        device: int,
        address: int,
        command: int,
        repeat: bool = False,
        modulation: int | None = None,
    ) -> None:
        """Initialize the three address/command fields."""
        bits(device, 7)
        bits(address, 6)
        bits(command, 7)
        super().__init__(modulation=self.CARRIER if modulation is None else modulation)
        self.device, self.address, self.command, self.repeat = (
            device,
            address,
            command,
            repeat,
        )

    @override
    def get_raw_timings(self) -> list[int]:
        """Encode the 24-bit biphase frame."""
        word = (
            (1 << 23)
            | (self.device << 16)
            | (self.address << 10)
            | (int(self.repeat) << 9)
            | (self.command << 1)
        )
        return runs(
            (level for bit in bits(word, 24) for level in (bit, 1 - bit)), self.UNIT
        )

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode this timing variant.

        The complete frame duration identifies the nominal clock. Captures with
        enough clock distortion to cross variants require a configured model.
        """
        if timings and timings[-1] < -4 * cls.UNIT:
            timings = timings[:-1]
        if not timings or not close(sum(abs(t) for t in timings), 48 * cls.UNIT, 0.12):
            return None
        try:
            levels = decode_levels(timings, cls.UNIT, maximum=2)
        except ValueError:
            return None
        if len(levels) != 48 or any(
            levels[i] == levels[i + 1] for i in range(0, 48, 2)
        ):
            return None
        value = number(levels[::2])
        if value & 0x800101 != 0x800000:
            return None
        return cls(
            device=(value >> 16) & 127,
            address=(value >> 10) & 63,
            command=(value >> 1) & 127,
            repeat=bool(value & 512),
        )


class CanalSatLDCommand(CanalSatCommand):
    """CanalSatLD's 320 us timing and 56 kHz carrier."""

    UNIT = 320
    CARRIER = 56000

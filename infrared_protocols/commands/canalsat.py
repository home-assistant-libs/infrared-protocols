"""CanalSat and CanalSatLD biphase infrared commands."""

from typing import ClassVar, Self, override

from . import Command
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
        """Decode either CanalSat timing variant."""
        levels: list[int] = []
        for duration in timings:
            if duration < -4 * cls.UNIT and len(levels) == 48:
                break
            count = round(abs(duration) / cls.UNIT)
            if count not in (1, 2) or not close(abs(duration), count * cls.UNIT):
                return None
            levels.extend([int(duration > 0)] * count)
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

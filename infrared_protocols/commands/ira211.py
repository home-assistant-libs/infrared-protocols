"""Siemens IRA211 thermostat commands in 800 us NRZ packets."""

from enum import IntEnum
from typing import Self, override

from . import Command
from ._timing import Reader, bits, close, number, runs


class Ira211Action(IntEnum):
    """Remote command identifiers."""

    TEMPERATURE_UP = 1
    TEMPERATURE_DOWN = 2
    MODE = 4
    FAN = 5
    POWER = 6
    SYNC = 7


class Ira211Mode(IntEnum):
    """Thermostat operating presets."""

    PROTECTION = 0
    TIMER = 85
    COMFORT = 170


class Ira211FanSpeed(IntEnum):
    """Thermostat fan levels."""

    AUTO = 3
    LOW = 12
    MEDIUM = 48
    HIGH = 192


_FIELDS = {
    Ira211Action.TEMPERATURE_UP: "tt",
    Ira211Action.TEMPERATURE_DOWN: "tt",
    Ira211Action.MODE: "m",
    Ira211Action.FAN: "f",
    Ira211Action.POWER: "ttmf",
    Ira211Action.SYNC: "ttmf",
}


def _reverse(value: int) -> int:
    return int(f"{value:08b}"[::-1], 2)


def _checksum(data: bytes) -> int:
    return _reverse((len(data) + sum(_reverse(byte) for byte in data)) & 255)


class Ira211Command(Command):
    """An IRA211 action and the state fields carried by that action.

    POWER has the remote's power-button semantics; callers must track the
    thermostat's current state. SYNC sends the complete state.
    """

    def __init__(
        self,
        *,
        action: Ira211Action = Ira211Action.SYNC,
        temperature: float | None = 20,
        mode: Ira211Mode | None = Ira211Mode.COMFORT,
        fan: Ira211FanSpeed | None = Ira211FanSpeed.AUTO,
        modulation: int = 38000,
    ) -> None:
        """Initialize valid half-degree settings."""
        fields = _FIELDS[Ira211Action(action)]
        if "t" in fields and (
            temperature is None or not 5 <= temperature <= 35 or temperature * 2 % 1
        ):
            raise ValueError("temperature must be 5..35 in half-degree steps")
        if "m" in fields and mode is None or "f" in fields and fan is None:
            raise ValueError("the action requires its mode and fan fields")
        super().__init__(modulation=modulation)
        self.action, self.temperature, self.mode, self.fan = (
            Ira211Action(action),
            temperature if "t" in fields else None,
            Ira211Mode(mode) if "m" in fields and mode is not None else None,
            Ira211FanSpeed(fan) if "f" in fields and fan is not None else None,
        )

    @override
    def get_raw_timings(self) -> list[int]:
        """Encode framed bytes and their checksum as merged NRZ runs."""
        values = [int(self.action)]
        if self.temperature is not None:
            values.extend([int(self.temperature), 5 if self.temperature % 1 else 0])
        if self.mode is not None:
            values.append(int(self.mode))
        if self.fan is not None:
            values.append(int(self.fan))
        wire = bytes([0x66] + [_reverse(value ^ 255) for value in values])
        wire += bytes([_checksum(wire)])
        levels = [bit for byte in wire for bit in [1, *bits(byte, 8), 0]]
        return [7600, -800, 800, -7600, *runs(levels, 800), 800, -7600]

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode the first complete action, allowing a following POWER/SYNC action."""
        r = Reader(timings=timings)
        try:
            r.expect(7600, -800, 800, -7600)
            unit = (timings[0] - timings[3]) / 19
            end = next(
                (i for i in range(r.pos, len(timings)) if timings[i] <= -9.25 * unit),
                len(timings),
            )
            body = timings[r.pos : end]
            if not body or not close(body[-1], unit):
                return None
            levels: list[int] = []
            for duration in body[:-1]:
                count = round(abs(duration) / unit)
                if not 1 <= count <= 9 or not close(
                    abs(duration), count * unit, 0, absolute=unit * 0.4
                ):
                    return None
                levels.extend([int(duration > 0)] * count)
            if len(levels) not in (40, 50, 70):
                return None
            packets = [levels[i : i + 10] for i in range(0, len(levels), 10)]
            if any(packet[0] != 1 or packet[-1] != 0 for packet in packets):
                return None
            wire = bytes(number(packet[1:9]) for packet in packets)
            if wire[0] != 0x66 or _checksum(wire[:-1]) != wire[-1]:
                return None
            values = [_reverse(byte) ^ 255 for byte in wire[1:-1]]
            action = Ira211Action(values.pop(0))
            fields = _FIELDS[action]
            if len(values) != len(fields):
                return None
            temperature = None
            mode = None
            fan = None
            if "t" in fields:
                whole, tenths = values.pop(0), values.pop(0)
                if tenths not in (0, 5):
                    return None
                temperature = whole + tenths / 10
            if "m" in fields:
                mode = Ira211Mode(values.pop(0))
            if "f" in fields:
                fan = Ira211FanSpeed(values.pop(0))
            return cls(action=action, temperature=temperature, mode=mode, fan=fan)
        except ValueError:
            return None

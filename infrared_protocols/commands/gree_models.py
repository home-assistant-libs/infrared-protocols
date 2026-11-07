"""Gree remote-model variants, alongside the original GreeAcCommand API."""

from dataclasses import dataclass
from enum import Enum, IntFlag, StrEnum
from typing import Self, override

from . import Command
from ._climate_fields import temperature_value
from ._timing import PulseTiming, Reader, byte_bits, pack_bytes
from .gree_ac import GreeAcFanSpeed, GreeAcMode


class GreeYx1ffFanSpeed(Enum):
    """YX1FF fan bits, with the byte-2 turbo bit included for high speed."""

    AUTO = 0
    QUIET = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 0x13


@dataclass(frozen=True, kw_only=True)
class GreeModelState:
    """Settings carried by a GreeModel packet, using its native enums and units."""

    power: bool | None = None
    mode: GreeAcMode | None = None
    temperature: float | None = None
    fan: GreeAcFanSpeed | GreeYx1ffFanSpeed | None = None
    swing_v: bool | None = None
    swing_h: bool | None = None
    is_fahrenheit: bool = False


class GreeModel(StrEnum):
    """Named remote layouts; a capture alone does not identify the model."""

    GENERIC = "generic"
    YAN = "yan"
    YAA = "yaa"
    YAC = "yac"
    YAC1FB9 = "yac1fb9"
    YB1FA = "yb1fa"
    YX1FF = "yx1ff"
    YAG = "yag"
    YAW1F = "yaw1f"


class GreeFeature(IntFlag):
    """Independent features where supported by the remote model."""

    NONE = 0
    TURBO = 16
    LIGHT = 32
    HEALTH = 64
    XFAN = 128


@dataclass(frozen=True)
class _Layout:
    features: int
    byte2: int = 0
    byte3: int = 0x50
    byte5: int = 0x20
    byte6: int = 0
    header_space: int = 4000
    gap: int = 19000


_LAYOUTS = {
    GreeModel.GENERIC: _Layout(0, byte3=0),
    GreeModel.YAN: _Layout(0xF0),
    GreeModel.YAA: _Layout(0xF0, byte6=32),
    GreeModel.YAC: _Layout(0xF0, byte6=32),
    GreeModel.YAC1FB9: _Layout(0xF0, byte6=32, header_space=4500, gap=19980),
    GreeModel.YB1FA: _Layout(0xB0),
    GreeModel.YX1FF: _Layout(0x20),
    GreeModel.YAG: _Layout(0, byte2=0x60, byte5=0x40),
    GreeModel.YAW1F: _Layout(0, byte2=0x60, byte5=0x80, header_space=4500, gap=19980),
}
_TIMING = PulseTiming(620, 540, 1600)
_FOLLOWUP = bytes([0, 0, 0, 0xA0, 0, 0, 0, 0xA0])


def _checksum(data: bytes | bytearray) -> int:
    return (
        (
            10
            + sum(value & 15 for value in data[:4])
            + sum(value >> 4 for value in data[4:7])
        )
        & 15
    ) << 4


class GreeModelCommand(Command):
    """Named remote variants, separate from GreeAcCommand's captured layout.

    Use GreeAcCommand for the captured YB1F2 layout, including latched swing
    axes and a retained power-off mode. This class covers the named GreeModel
    layouts and clears mode bits on power-off. GENERIC is the legacy basic
    layout, not automatic model detection or a fallback for every Gree remote.

    YAC/YAG/YAW1F use absolute vane fields, YB1FA/YX1FF gate them with the
    swing-enable bit, and GENERIC/YAN/YAA/YAC1FB9 accept either representation.
    The configured remote selects the decoder; shared framing cannot identify it.
    """

    def __init__(
        self,
        *,
        model: GreeModel,
        mode: GreeAcMode | None,
        temperature: float,
        power: bool = True,
        fan: GreeAcFanSpeed | GreeYx1ffFanSpeed | None = None,
        swing_v: bool = False,
        swing_h: bool = False,
        features: GreeFeature | None = None,
        sleep: bool = False,
        is_fahrenheit: bool = False,
        modulation: int = 38000,
    ) -> None:
        """Build a 16..30 °C state, or 60..86 °F with is_fahrenheit=True.

        YX1FF exposes vertical swing only. YAC, YAG and YAW1F expose both axes.
        Feature defaults enable the display light where supported.
        """
        model = GreeModel(model)
        layout = _LAYOUTS[model]
        if is_fahrenheit:
            temperature_value(temperature, 60, 86)
            half_steps = max(0, (10 * int(temperature) - 608 + 8) // 9)
            temperature = 16 + half_steps / 2
        else:
            temperature_value(temperature, 16, 30)
        both_axes = model in (GreeModel.YAC, GreeModel.YAG, GreeModel.YAW1F)
        if swing_h and not both_axes:
            raise ValueError("horizontal swing is unavailable on this model")
        if model == GreeModel.GENERIC and (swing_v or swing_h):
            raise ValueError("the generic transmitter has no swing field")
        if sleep and model not in (GreeModel.YX1FF, GreeModel.YAC1FB9):
            raise ValueError("sleep is unavailable on this model")
        feature_bits = layout.features & 32 if features is None else int(features)
        if feature_bits & ~layout.features:
            raise ValueError("unsupported Gree feature for this model")
        if model == GreeModel.YB1FA and feature_bits & GreeFeature.TURBO:
            fan = GreeAcFanSpeed.HIGH
        if model == GreeModel.YX1FF:
            if fan is not None and not isinstance(fan, GreeYx1ffFanSpeed):
                raise TypeError("YX1FF requires GreeYx1ffFanSpeed")
            fan = GreeYx1ffFanSpeed.AUTO if fan is None else fan
        else:
            if fan is not None and not isinstance(fan, GreeAcFanSpeed):
                raise TypeError("this model requires GreeAcFanSpeed")
            fan = GreeAcFanSpeed.AUTO if fan is None else fan
        data = bytearray(
            [
                (fan.value & 3) << 4 | (int(GreeAcMode(mode)) | 8 if power else 0),
                int(temperature) - 16,
                feature_bits | layout.byte2,
                layout.byte3,
                0,
                layout.byte5,
                layout.byte6,
                0,
            ]
        )
        if model in (GreeModel.YB1FA, GreeModel.YX1FF) and power:
            data[2] |= 64
        if model == GreeModel.YX1FF and fan == GreeYx1ffFanSpeed.HIGH:
            data[2] |= 16
        if both_axes:
            data[4] = int(swing_v) | int(swing_h) << 4
        elif model in (GreeModel.YAN, GreeModel.YB1FA):
            data[4] = int(swing_v)
        elif model == GreeModel.YX1FF:
            data[4] = 0x11 if swing_v else 0
        if model not in (GreeModel.GENERIC, GreeModel.YAN) and (
            swing_v or (swing_h and model in (GreeModel.YAG, GreeModel.YAW1F))
        ):
            data[0] |= 64
        data[0] |= 128 if sleep else 0
        data[3] |= (8 if is_fahrenheit else 0) | (4 if temperature % 1 else 0)
        data[7] = _checksum(data)
        super().__init__(modulation=modulation)
        self.model, self.data = model, bytes(data)

    @property
    def features(self) -> GreeFeature:
        """Return independent features, excluding model-specific power and fan bits."""
        return GreeFeature(self.data[2] & _LAYOUTS[self.model].features)

    @property
    def sleep(self) -> bool | None:
        """Return sleep where the selected remote defines that flag."""
        if self.model in (GreeModel.YX1FF, GreeModel.YAC1FB9):
            return bool(self.data[0] & 128)
        return None

    @property
    def _is_fahrenheit(self) -> bool:
        """Return the remote's display-unit flag."""
        return bool(self.data[3] & 8)

    @property
    def _temperature(self) -> float:
        """Return the set point in the remote's display units."""
        half_steps = 2 * (self.data[1] & 15) + bool(self.data[3] & 4)
        if self._is_fahrenheit:
            return (608 + 9 * half_steps) // 10
        return 16 + half_steps / 2

    @property
    def state(self) -> GreeModelState:
        """Read common settings without discarding received auxiliary fields."""
        data, model = self.data, self.model
        if len(data) != 8 or data[7] & 0xF0 != _checksum(data):
            raise ValueError("invalid Gree checksum")
        if model == GreeModel.YAC and data[3] & 0xF0 == 0x70:
            raise ValueError("YAC follow-up carries no climate state")
        if model == GreeModel.YAW1F and data == _FOLLOWUP:
            raise ValueError("YAW1F follow-up carries no climate state")
        temperature_value(
            16 + (data[1] & 15) + (0.5 if data[3] & 4 else 0), 16, 30, 0.5
        )
        mode = GreeAcMode(data[0] & 7)
        code = data[0] >> 4 & 3
        fan = (
            GreeYx1ffFanSpeed(code | (data[2] & 16))
            if model == GreeModel.YX1FF
            else GreeAcFanSpeed(code)
        )
        if model == GreeModel.YB1FA and data[2] & 16:
            fan = GreeAcFanSpeed.HIGH
        vertical = data[4] & 15
        swinging = bool(data[0] & 64)
        swing_v = swinging or vertical in (1, 7, 9, 11)
        swing_h: bool | None = None
        if model in (GreeModel.YAC, GreeModel.YAG, GreeModel.YAW1F):
            swing_v = vertical in (1, 7, 9, 11)
            swing_h = data[4] >> 4 & 7 == 1
        elif model in (GreeModel.YB1FA, GreeModel.YX1FF):
            timer_ones, timer_tens = data[2] & 15, data[1] >> 5 & 3
            timer_minutes = 60 * (10 * timer_tens + timer_ones) + (
                30 if data[1] & 16 else 0
            )
            valid_vertical = (1, 7, 9, 11) if swinging else (0, 2, 3, 4, 5, 6)
            horizontal = int(swinging) if model == GreeModel.YX1FF else 0
            if (
                timer_ones > 9
                or timer_minutes > 1440
                or bool(data[2] & 64) != bool(data[0] & 8)
                or data[3] & 0xF3 != 0x50
                or vertical not in valid_vertical
                or data[4] >> 4 != horizontal
                or data[5] & 0xB8 != 0x20
                or data[6] != 0
                or data[7] & 15
                or model == GreeModel.YX1FF
                and data[2] & 16
                and code != 3
            ):
                raise ValueError("invalid Gree model-A fields")
            swing_v = swinging
        return GreeModelState(
            power=bool(data[0] & 8),
            mode=mode if data[0] & 8 else None,
            temperature=self._temperature,
            is_fahrenheit=self._is_fahrenheit,
            fan=fan,
            swing_v=swing_v,
            swing_h=swing_h,
        )

    def _encode(self, data: bytes) -> list[int]:
        layout = _LAYOUTS[self.model]
        return [
            9000,
            -layout.header_space,
            *_TIMING.encode(byte_bits(data[:4])),
            *_TIMING.encode((0, 1, 0)),
            620,
            -layout.gap,
            *_TIMING.encode(byte_bits(data[4:])),
            620,
        ]

    @override
    def get_raw_timings(self) -> list[int]:
        """Encode the state and the YAW1F mandatory follow-up when applicable."""
        result = self._encode(self.data)
        if self.model == GreeModel.YAW1F:
            result.extend((-40000, *self._encode(_FOLLOWUP)))
        return result

    @staticmethod
    def _read(reader: Reader, model: GreeModel) -> bytes:
        layout = _LAYOUTS[model]
        reader.expect(9000, -layout.header_space)
        first = reader.read_bits(_TIMING, 32)
        if reader.read_bits(_TIMING, 3) != [0, 1, 0]:
            raise ValueError("invalid Gree divider")
        reader.expect(620, -layout.gap)
        data = pack_bytes(first + reader.read_bits(_TIMING, 32))
        reader.expect(620)
        return data

    @classmethod
    def from_raw_timings(cls, timings: list[int], *, model: GreeModel) -> Self | None:
        """Decode using an explicit remote model; validate any YAW1F follow-up."""
        model = GreeModel(model)
        reader = Reader(timings=timings)
        try:
            data = cls._read(reader, model)
            if model == GreeModel.YAW1F and len(timings) - reader.pos > 1:
                reader.expect(-40000)
                if cls._read(reader, model) != _FOLLOWUP:
                    raise ValueError("invalid YAW1F follow-up")
            reader.end()
            result = cls.__new__(cls)
            Command.__init__(result, modulation=38000)
            result.data, result.model = data, model
            _ = result.state
            return result
        except ValueError:
            return None

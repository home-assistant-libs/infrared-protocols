"""Toshiba variable-length climate packets and native remote variants."""

from dataclasses import dataclass
from enum import IntEnum, StrEnum
from functools import reduce
from operator import xor
from typing import ClassVar, Self, override

from . import Command
from ._climate_fields import temperature_value
from ._timing import PulseTiming, Reader, byte_bits, pack_bytes


class ToshibaMode(IntEnum):
    """Toshiba operating modes."""

    AUTO = 0x0
    COOL = 0x1
    DRY = 0x2
    HEAT = 0x3
    FAN_ONLY = 0x4


class ToshibaFanSpeed(IntEnum):
    """Native fan field, preserving the two intermediate speeds."""

    AUTO = 0
    QUIET = 1
    LOW = 2
    LOW_PLUS = 3
    MEDIUM = 4
    MEDIUM_PLUS = 5
    HIGH = 6


@dataclass(frozen=True, kw_only=True)
class ToshibaState:
    """Settings carried by a Toshiba packet, using its native enums and units."""

    power: bool | None = None
    mode: ToshibaMode | None = None
    temperature: int | None = None
    fan: ToshibaFanSpeed | None = None


class ToshibaMotion(IntEnum):
    """Short WH-TA15PE actions; swing is a toggle."""

    VANE_STEP = 0
    SWING_TOGGLE = 4


class ToshibaPreset(StrEnum):
    """WH-TA15PE operating presets."""

    NONE = "none"
    BOOST = "boost"
    ECO = "eco"
    FIREPLACE_1 = "fireplace_1"
    FIREPLACE_2 = "fireplace_2"
    FROST_PROTECTION = "frost_protection"
    HADA_CARE = "hada_care"
    SLEEP_1H = "sleep_1h"
    SLEEP_3H = "sleep_3h"
    SLEEP_5H = "sleep_5h"
    SLEEP_9H = "sleep_9h"


class ToshibaPowerSelection(IntEnum):
    """Compressor power selection, distinct from the on/off state."""

    PERCENT_100 = 0
    PERCENT_75 = 1
    PERCENT_50 = 2
    SILENT_1 = 3
    SILENT_2 = 4


class ToshibaSeiyaSwing(IntEnum):
    """Momentary swing requests; UNCHANGED carries no new swing state."""

    BOTH = 1
    OMNI = 2
    VERTICAL = 8
    HORIZONTAL = 9
    UNCHANGED = 0x17


def _packet(payload: bytes) -> bytes:
    length = len(payload) - 1
    return (
        bytes([0xF2, 0x0D, length, length ^ 255])
        + payload
        + bytes([reduce(xor, payload, 0)])
    )


class ToshibaCommand(Command):
    """Toshiba packets retain all bytes; climate() builds a generic state."""

    HEADER: ClassVar[tuple[int, ...]] = (4380, -4370)
    TIMING: ClassVar[PulseTiming] = PulseTiming(540, 540, 1620)
    GAP: ClassVar[int] = 5480
    FINAL_GAP: ClassVar[bool] = True
    LENGTHS: ClassVar[tuple[int, ...]] = (9,)

    def __init__(self, *, data: bytes) -> None:
        """Validate a complete packet, including length complement and checksum."""
        super().__init__(modulation=38000)
        self.data = bytes(data)
        _ = self.state

    @classmethod
    def climate(
        cls,
        *,
        mode: ToshibaMode | None,
        temperature: int,
        power: bool = True,
        fan: ToshibaFanSpeed = ToshibaFanSpeed.AUTO,
    ) -> Self:
        """Build a generic whole-degree 17..30 °C state."""
        temp = temperature_value(temperature, 17, 30)
        fan_code = int(ToshibaFanSpeed(fan))
        payload = bytes(
            [
                1,
                temp << 4,
                (int(ToshibaMode(mode)) if power else 7) | fan_code << 5,
                0,
            ]
        )
        return cls(data=_packet(payload))

    @property
    def state(self) -> ToshibaState:
        """Decode basic mode, fan and temperature; motion packets carry no state."""
        data = self.data
        if (
            len(data) not in self.LENGTHS
            or data[:2] != b"\xf2\x0d"
            or data[2] != len(data) - 6
            or data[2] ^ data[3] != 255
            or reduce(xor, data[4:], 0)
        ):
            raise ValueError("invalid Toshiba packet header, size or checksum")
        if len(self.data) == 7:
            if self.data[4] != 0x21:
                raise ValueError("unknown Toshiba motion format")
            ToshibaMotion(self.data[5])
            return ToshibaState()
        if len(self.data) == 9 and self.data[4] != 1:
            raise ValueError("not a Toshiba climate command")
        mode_code = self.data[6] & 15
        power = mode_code != 7
        mode = ToshibaMode(mode_code) if power else None
        frost = len(self.data) == 10 and self.data[4] == 9 and self.data[8] == 4
        temp = (self.data[5] >> 4) + (1 if frost else 17)
        temperature_value(temp, 5 if frost else 17, 13 if frost else 30)
        fan_code = self.data[6] >> 5
        if fan_code > 6 or self.data[6] & 16 or self.data[5] & 15:
            raise ValueError("invalid Toshiba fan or temperature field")
        fan = ToshibaFanSpeed(fan_code)
        return ToshibaState(power=power, mode=mode, temperature=temp, fan=fan)

    @override
    def get_raw_timings(self) -> list[int]:
        """Transmit the protocol's two identical packet copies."""
        frame = [
            *self.HEADER,
            *self.TIMING.encode(byte_bits(self.data, lsb=False)),
            self.TIMING.mark,
        ]
        if len(self.data) == 7 and self.data[5] == ToshibaMotion.VANE_STEP:
            return frame + [-self.GAP]
        return frame + [-self.GAP] + frame + ([-self.GAP] if self.FINAL_GAP else [])

    @classmethod
    def _read(cls, reader: Reader) -> bytes:
        reader.expect(*cls.HEADER)
        header = pack_bytes(reader.read_bits(cls.TIMING, 32), lsb=False)
        length = header[2] + 6
        if length not in cls.LENGTHS or header[2] ^ header[3] != 255:
            raise ValueError("invalid Toshiba length field")
        data = header + pack_bytes(
            reader.read_bits(cls.TIMING, (length - 4) * 8), lsb=False
        )
        reader.expect(cls.TIMING.mark)
        return data

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode one complete packet or two identical protocol copies."""
        reader = Reader(timings=timings)
        try:
            data = cls._read(reader)
            if len(timings) - reader.pos > 1:
                reader.expect(-cls.GAP)
                if cls._read(reader) != data:
                    raise ValueError("Toshiba copies differ")
            reader.end()
            return cls(data=data)
        except ValueError:
            return None


class ToshibaRasB10n3kv2Command(ToshibaCommand):
    """RAS-B13 remote family uses distinct timings for the generic state."""

    HEADER = (4400, -4300)
    TIMING = PulseTiming(580, 490, 1600)
    GAP = 7400


class ToshibaSeiyaCommand(ToshibaCommand):
    """Seiya 88-bit state with a momentary swing request."""

    HEADER = (4630, -4450)
    TIMING = PulseTiming(625, 490, 1570)
    GAP = 5830
    FINAL_GAP = False
    LENGTHS = (11,)

    @classmethod
    def climate(
        cls,
        *,
        mode: ToshibaMode | None,
        temperature: int,
        power: bool = True,
        fan: ToshibaFanSpeed | None = ToshibaFanSpeed.AUTO,
        swing: ToshibaSeiyaSwing = ToshibaSeiyaSwing.UNCHANGED,
    ) -> Self:
        """Build a Seiya state; send swing requests only when a change is intended."""
        temp = temperature_value(temperature, 17, 30)
        fan_code = int(ToshibaFanSpeed(fan)) if power else 0
        code = int(ToshibaMode(mode)) | fan_code << 5 if power else 7
        return cls(
            data=_packet(bytes([1, temp << 4, code, 0, 0x21, ToshibaSeiyaSwing(swing)]))
        )

    @property
    def state(self) -> ToshibaState:
        """Validate Seiya auxiliary fields and recover common settings."""
        state = super().state
        if self.data[4] != 1 or self.data[7:9] != b"\x00\x21":
            raise ValueError("invalid Seiya feature fields")
        ToshibaSeiyaSwing(self.data[9])
        return ToshibaState(
            power=state.power,
            mode=state.mode,
            temperature=state.temperature,
            fan=state.fan if state.power else None,
        )

    @property
    def swing(self) -> ToshibaSeiyaSwing:
        """Return the momentary swing request."""
        _ = self.state
        return ToshibaSeiyaSwing(self.data[9])


class ToshibaRas25j2kvsgNdCommand(ToshibaCommand):
    """WH-TA15PE packets with presets, power selection and separate motion actions."""

    LENGTHS = (7, 9, 10, 11, 12)

    @property
    def state(self) -> ToshibaState:
        """Validate the selected extended packet layout and decode basic state."""
        state = super().state
        data = self.data
        if len(data) == 7:
            return state
        if data[7] & 0x3C or data[7] >> 6 == 3 or data[7] & 3 == 1:
            raise ValueError("invalid Toshiba power or fireplace field")
        if len(data) == 9:
            valid = data[4] == 1
        elif len(data) == 10:
            valid = data[4] == 9 and data[8] in (1, 2, 3, 4, 10)
        elif len(data) == 11:
            valid = data[4] == 1 and data[8:10] == b"\x21\x17"
        else:
            valid = (
                data[4] == 11
                and data[8] in (4, 12, 20, 36)
                and data[9:11] == b"\x7f\x03"
                and data[6] >> 5 == 0
            )
        if len(data) == 10 and data[8] in (2, 10) and data[7] >> 6:
            raise ValueError("silent power selection excludes percentage limits")
        if not valid:
            raise ValueError("invalid Toshiba preset packet")
        if len(data) != 9 and data[7] & 3:
            raise ValueError("fireplace cannot be combined with another preset")
        if (data[7] & 3 or len(data) == 10 and data[8] == 4) and (
            state.mode != ToshibaMode.HEAT or not state.power
        ):
            raise ValueError("heating preset outside heat mode")
        if state.mode == ToshibaMode.FAN_ONLY:
            return ToshibaState(power=state.power, mode=state.mode, fan=state.fan)
        return state

    @property
    def retained_temperature(self) -> int | None:
        """Return the stored temperature field, including fan-only packets."""
        return super().state.temperature

    @property
    def action(self) -> ToshibaMotion | None:
        """Return the momentary action, absent in full state packets."""
        _ = self.state
        return ToshibaMotion(self.data[5]) if len(self.data) == 7 else None

    @property
    def preset(self) -> ToshibaPreset | None:
        """Return the encoded preset; motion commands carry none."""
        _ = self.state
        data = self.data
        if len(data) == 7:
            return None
        if len(data) == 9:
            return {2: ToshibaPreset.FIREPLACE_1, 3: ToshibaPreset.FIREPLACE_2}.get(
                data[7] & 3, ToshibaPreset.NONE
            )
        if len(data) == 10:
            return {
                1: ToshibaPreset.BOOST,
                3: ToshibaPreset.ECO,
                4: ToshibaPreset.FROST_PROTECTION,
            }.get(data[8], ToshibaPreset.NONE)
        if len(data) == 11:
            return ToshibaPreset.HADA_CARE
        return {
            4: ToshibaPreset.SLEEP_1H,
            12: ToshibaPreset.SLEEP_3H,
            20: ToshibaPreset.SLEEP_5H,
            36: ToshibaPreset.SLEEP_9H,
        }[data[8]]

    @property
    def power_selection(self) -> ToshibaPowerSelection | None:
        """Return the compressor power or silent setting."""
        _ = self.state
        if len(self.data) == 7:
            return None
        if len(self.data) == 10 and self.data[8] in (2, 10):
            return (
                ToshibaPowerSelection.SILENT_1
                if self.data[8] == 2
                else ToshibaPowerSelection.SILENT_2
            )
        return ToshibaPowerSelection(self.data[7] >> 6)

    @classmethod
    def climate(
        cls,
        *,
        mode: ToshibaMode | None,
        temperature: int | None = None,
        power: bool = True,
        fan: ToshibaFanSpeed = ToshibaFanSpeed.AUTO,
        preset: ToshibaPreset = ToshibaPreset.NONE,
        power_selection: ToshibaPowerSelection = ToshibaPowerSelection.PERCENT_100,
    ) -> Self:
        """Build a state with common or native fan selections.

        Fan-only accepts None, encoding 17 °C in the inactive field. Use
        retained_temperature to preserve a received fan-only packet's field.
        Frost protection accepts 5..13 °C in heat mode. Fireplace presets also
        require heat. Sleep uses automatic fan; silent power excludes presets.
        """
        preset, power_selection = (
            ToshibaPreset(preset),
            ToshibaPowerSelection(power_selection),
        )
        frost = preset == ToshibaPreset.FROST_PROTECTION
        if temperature is not None:
            temperature_value(temperature, 5 if frost else 17, 13 if frost else 30)
        elif mode == ToshibaMode.FAN_ONLY:
            temperature = 17
        else:
            raise ValueError("temperature is required for this mode")
        if preset in (
            ToshibaPreset.FROST_PROTECTION,
            ToshibaPreset.FIREPLACE_1,
            ToshibaPreset.FIREPLACE_2,
        ) and (mode != ToshibaMode.HEAT or not power):
            raise ValueError("heating presets require heat mode and power on")
        if power_selection >= 3 and preset != ToshibaPreset.NONE:
            raise ValueError("silent power selection cannot be combined with a preset")
        fan_code = int(ToshibaFanSpeed(fan))
        if mode == ToshibaMode.DRY and fan_code:
            raise ValueError("dry mode requires automatic fan")
        sleep_hours = {
            ToshibaPreset.SLEEP_1H: 1,
            ToshibaPreset.SLEEP_3H: 3,
            ToshibaPreset.SLEEP_5H: 5,
            ToshibaPreset.SLEEP_9H: 9,
        }.get(preset)
        if sleep_hours is not None and fan_code:
            raise ValueError("sleep presets require automatic fan")
        flags = int(power_selection) << 6 if power_selection < 3 else 0
        flags |= {ToshibaPreset.FIREPLACE_1: 2, ToshibaPreset.FIREPLACE_2: 3}.get(
            preset, 0
        )
        payload = bytearray(
            [
                1,
                (temperature - (1 if frost else 17)) << 4,
                (int(ToshibaMode(mode)) if power else 7) | fan_code << 5,
                flags,
            ]
        )
        if sleep_hours is not None:
            payload[0] = 11
            payload.extend((sleep_hours << 2, 0x7F, 3))
        elif preset == ToshibaPreset.HADA_CARE:
            payload.extend((0x21, 0x17))
        elif (
            preset
            in (ToshibaPreset.BOOST, ToshibaPreset.ECO, ToshibaPreset.FROST_PROTECTION)
            or power_selection >= 3
        ):
            payload[0] = 9
            payload.append(
                {
                    ToshibaPreset.BOOST: 1,
                    ToshibaPreset.ECO: 3,
                    ToshibaPreset.FROST_PROTECTION: 4,
                }.get(preset, 2 if power_selection == 3 else 10)
            )
        return cls(data=_packet(bytes(payload)))

    @classmethod
    def motion(cls, *, action: ToshibaMotion) -> Self:
        """Build a separate vane-step or swing-toggle command."""
        return cls(data=_packet(bytes([0x21, ToshibaMotion(action)])))

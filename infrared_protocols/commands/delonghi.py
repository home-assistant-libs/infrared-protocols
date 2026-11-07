"""DeLonghi ARC43xxx portable air-conditioner state commands."""

from dataclasses import dataclass
from enum import IntEnum

from ._climate import ClimatePacket
from ._climate_fields import temperature_value
from ._timing import PulseTiming


class DelonghiMode(IntEnum):
    """Delonghi operating modes."""

    COOL = 0x0
    DRY = 0x2
    FAN_ONLY = 0x4
    HEAT = 0x6
    AUTO = 0x8


class DelonghiFanSpeed(IntEnum):
    """Delonghi fan speeds."""

    AUTO = 0x0
    HIGH = 0x1
    MEDIUM = 0x2
    LOW = 0x3


@dataclass(frozen=True, kw_only=True)
class DelonghiState:
    """Settings carried by a Delonghi packet, using its native enums and units."""

    power: bool | None = None
    mode: DelonghiMode | None = None
    temperature: int | None = None
    fan: DelonghiFanSpeed | None = None
    is_fahrenheit: bool = False


class DelonghiCommand(ClimatePacket[DelonghiState]):
    """DeLonghi state; the temperature range depends on operating mode."""

    HEADER = (9000, -4500)
    TIMING = PulseTiming(465, 670, 1750)
    LENGTH = 8

    def __init__(
        self,
        *,
        mode: DelonghiMode | None,
        temperature: int | None,
        is_fahrenheit: bool = False,
        power: bool = True,
        fan: DelonghiFanSpeed = DelonghiFanSpeed.AUTO,
        boost: bool = False,
        sleep: bool = False,
        retained_mode: DelonghiMode | None = None,
    ) -> None:
        """Build a command: heat 13..27 °C, other modes 17..32 °C, or 64..90 °F.

        The Celsius heat field uses a 12 °C offset. An off command uses the
        cool temperature offset, even with a retained mode.
        Fahrenheit auto/dry packets can use None for the zero placeholder.
        Off packets also accept None, encoding a zero temperature field. Use
        retained_temperature to preserve a received off packet's stored field.
        retained_mode preserves nonzero mode bits on received off packets;
        omit it for the default off layout, which clears those bits.
        """
        if retained_mode is not None and power:
            raise ValueError("retained_mode is only supported for off packets")
        mode_code = (
            int(DelonghiMode(mode)) | 1
            if power
            else int(DelonghiMode(retained_mode))
            if retained_mode is not None
            else 0
        )
        heat = mode == DelonghiMode.HEAT
        if temperature is None:
            if power and not (
                is_fahrenheit and mode in (DelonghiMode.AUTO, DelonghiMode.DRY)
            ):
                raise ValueError("temperature is required for this mode and unit")
            temp = 0
        elif is_fahrenheit:
            temperature_value(temperature, 64, 90)
            temp = int(temperature) - 63
        else:
            temperature_value(temperature, 13 if heat else 17, 27 if heat else 32)
            temp = (
                int(temperature) - 12
                if heat and power
                else max(17, int(temperature)) - 17
            )
        data = bytes(
            [
                0x53,
                temp | int(DelonghiFanSpeed(fan)) << 5 | int(is_fahrenheit) << 7,
                mode_code | (16 if boost else 0) | (32 if sleep else 0),
                0,
                0,
                0,
                0,
            ]
        )
        super().__init__(data=data + bytes([self.checksum(data)]))

    @property
    def retained_mode(self) -> DelonghiMode | None:
        """Return the inactive mode field on an off packet, if identified.

        COOL is code zero, also used when the sender clears this field. It
        does not establish which mode the unit was in before powering off.
        """
        code = self.data[2] & 14
        return (
            DelonghiMode(code)
            if not self.state.power and code in DelonghiMode
            else None
        )

    @property
    def retained_temperature(self) -> int | None:
        """Return the temperature field retained even when power is off."""
        if self.state.power:
            return self.state.temperature
        code = self.data[1] & 31
        if self.data[1] & 128:
            return code + 63 if code else None
        return code + 17

    @property
    def boost(self) -> bool:
        """Return the remote's boost flag."""
        return bool(self.data[2] & 16)

    @property
    def sleep(self) -> bool:
        """Return the remote's sleep flag."""
        return bool(self.data[2] & 32)

    @classmethod
    def parse(cls, data: bytes) -> DelonghiState:
        """Validate and recover the state."""
        cls._validate_packet(data)
        if data[0] != 0x53:
            raise ValueError("invalid DeLonghi address")
        power = bool(data[2] & 1)
        mode = DelonghiMode(data[2] & 14) if power else None
        heat = power and mode == DelonghiMode.HEAT
        is_fahrenheit = bool(data[1] & 128)
        temperature = (data[1] & 31) + (63 if is_fahrenheit else 12 if heat else 17)
        if (
            is_fahrenheit
            and data[1] & 31 == 0
            and (not power or mode in (DelonghiMode.AUTO, DelonghiMode.DRY))
        ):
            temperature = None
        else:
            temperature_value(
                temperature,
                64 if is_fahrenheit else 13 if heat else 17,
                90 if is_fahrenheit else 27 if heat else 32,
            )
        return DelonghiState(
            power=power,
            mode=mode,
            temperature=temperature if power else None,
            fan=DelonghiFanSpeed(data[1] >> 5 & 3),
            is_fahrenheit=is_fahrenheit,
        )

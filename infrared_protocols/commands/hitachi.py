"""Hitachi 344-bit and 424-bit commands with complementary byte pairs."""

from dataclasses import dataclass
from enum import IntEnum
from typing import ClassVar

from ._climate import ClimatePacket
from ._climate_fields import decoded, selection, temperature_value
from ._timing import PulseTiming


class HitachiMode(IntEnum):
    """Hitachi operating modes; AUTO is currently receive-only."""

    AUTO = 7

    FAN_ONLY = 0x1
    COOL = 0x3
    DRY = 0x5
    HEAT = 0x6


class HitachiFanSpeed(IntEnum):
    """Hitachi fan speeds; MAXIMUM is currently receive-only."""

    MAXIMUM = 6

    QUIET = 0x1
    LOW = 0x2
    MEDIUM = 0x3
    HIGH = 0x4
    AUTO = 0x5


@dataclass(frozen=True, kw_only=True)
class HitachiState:
    """Settings carried by a Hitachi packet, using its native enums and units."""

    power: bool | None = None
    mode: HitachiMode | None = None
    temperature: int | None = None
    fan: HitachiFanSpeed | None = None
    swing_v: bool | None = None
    swing_h: bool | None = None


_MODES = {
    HitachiMode.FAN_ONLY: 1,
    HitachiMode.COOL: 3,
    HitachiMode.DRY: 5,
    HitachiMode.HEAT: 6,
}
_FANS = {
    HitachiFanSpeed.QUIET: 1,
    HitachiFanSpeed.LOW: 2,
    HitachiFanSpeed.MEDIUM: 3,
    HitachiFanSpeed.HIGH: 4,
    HitachiFanSpeed.AUTO: 5,
}


class HitachiButton(IntEnum):
    """The action byte accompanying state; SWING_V toggles the vertical vane."""

    POWER = 0x13
    SLEEP = 0x31
    MODE = 0x41
    FAN = 0x42
    TEMPERATURE_DOWN = 0x43
    TEMPERATURE_UP = 0x44
    SWING_V = 0x81
    SWING_H = 0x8C
    MILDEW_PROOF = 0xE2


class HitachiAc344Command(ClimatePacket[HitachiState]):
    """Hitachi 344 state; use SWING_V only when a vertical change is intended."""

    HEADER = (3300, -1700)
    TIMING = PulseTiming(400, 500, 1250)
    LENGTH = 43
    GAP = 100000
    EXTENDED: ClassVar[bool] = False

    def __init__(
        self,
        *,
        mode: HitachiMode,
        temperature: int,
        power: bool = True,
        fan: HitachiFanSpeed = HitachiFanSpeed.AUTO,
        swing_v: bool = False,
        horizontal_position: int = 3,
        button: HitachiButton = HitachiButton.POWER,
        mildew_proof: bool = False,
    ) -> None:
        """Build 16..32 °C state; horizontal 0 swings, 1..5 are fixed positions.

        Dry supports auto, quiet and low fan. Fan-only has no automatic fan.
        swing_v records the state; the SWING_V button requests the physical toggle.
        """
        temperature_value(temperature, 16, 32)
        if not 0 <= horizontal_position <= 5:
            raise ValueError("horizontal_position must be 0..5")
        if mode == HitachiMode.DRY and fan not in (
            HitachiFanSpeed.AUTO,
            HitachiFanSpeed.QUIET,
            HitachiFanSpeed.LOW,
        ):
            raise ValueError("dry mode supports automatic, quiet and low fan")
        if mode == HitachiMode.FAN_ONLY and fan == HitachiFanSpeed.AUTO:
            raise ValueError("fan-only mode requires a fixed fan speed")
        data = bytearray(self.LENGTH)
        fields = {
            3: 0x40,
            5: 255,
            7: 0xCC,
            9: 0x98 if fan == HitachiFanSpeed.QUIET else 0x92,
            11: HitachiButton(button),
            13: temperature << 2,
            25: selection(fan, _FANS) << 4 | selection(mode, _MODES),
            27: 0xF1 if power else 0xE1,
            29: 1,
            31: 0 if self.EXTENDED else 1,
            33: 128,
            35: horizontal_position,
            37: (1 if self.EXTENDED else 0)
            | (32 if swing_v else 0)
            | (4 if mildew_proof else 0),
            39: 0x88 if self.EXTENDED else 0,
        }
        if not power and mildew_proof and not self.EXTENDED:
            fields[9] = 0xA5
        if self.EXTENDED:
            fields.update({45: 255, 47: 255, 49: 255, 51: 255})
        data[:3] = bytes([1, 16, 0])
        for index, value in fields.items():
            data[index] = value
        for index in range(3, self.LENGTH, 2):
            data[index + 1] = data[index] ^ 255
        super().__init__(data=bytes(data))

    @property
    def horizontal_position(self) -> int:
        """Return the native horizontal vane setting: 0 swings, 1..5 are fixed."""
        return self.data[35] & 7

    @property
    def mildew_proof(self) -> bool:
        """Return the remote's mildew-prevention setting."""
        return bool(self.data[37] & 4)

    @property
    def button(self) -> HitachiButton:
        """Return the accompanying action."""
        return HitachiButton(self.data[11])

    @classmethod
    def parse(cls, data: bytes) -> HitachiState:
        """Validate all complements and decode the common state."""
        if (
            len(data) != cls.LENGTH
            or data[:3] != bytes([1, 16, 0])
            or any(data[i] ^ data[i + 1] != 255 for i in range(3, cls.LENGTH, 2))
        ):
            raise ValueError("invalid Hitachi packet or byte complement")
        if data[27] not in (0xE1, 0xF1):
            raise ValueError("invalid Hitachi power byte")
        HitachiButton(data[11])
        temperature = data[13] >> 2
        temperature_value(temperature, 16, 32)
        return HitachiState(
            power=data[27] == 0xF1,
            mode=HitachiMode.AUTO
            if data[25] & 15 == (14 if cls.EXTENDED else 7)
            else decoded(data[25] & 15, _MODES),
            temperature=temperature,
            fan=HitachiFanSpeed.MAXIMUM
            if data[25] >> 4 == 6
            else decoded(data[25] >> 4, _FANS),
            swing_v=bool(data[37] & 32),
            swing_h=data[35] & 7 == 0,
        )


class HitachiAc424Command(HitachiAc344Command):
    """Hitachi 424-bit extended state."""

    HEADER = (3416, -1604)
    TIMING = PulseTiming(463, 372, 1208)
    LENGTH = 53
    EXTENDED = True

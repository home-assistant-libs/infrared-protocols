"""Panasonic air-conditioner IR protocol.

Panasonic A/C remotes use the Kaseikyo (AEHA) format with the Panasonic vendor
address ``0x2002``. The state is sent as two Kaseikyo frames (a fixed 8-byte
preamble frame followed by a 19-byte payload frame) separated by an inter-frame
gap, so this module builds the state bytes and delegates the physical-layer
encoding to :class:`~infrared_protocols.commands.kaseikyo.KaseikyoCommand`.

Without a model, the encoder retains the original regional frame layout. Named
models use the 216-bit layouts documented by ESPHome's Panasonic IR component:
https://github.com/esphome/esphome/tree/dev/esphome/components/panasonic_ir
"""

from dataclasses import dataclass
from enum import Enum, IntEnum, StrEnum
from typing import Self

from .kaseikyo import KaseikyoCommand

PANASONIC_AC_ADDRESS = 0x2002

MIN_TEMP = 16
MAX_TEMP = 30

# Fixed "magic" bytes that frame the state; they must be emitted verbatim.
_FRAME1 = [0x02, 0x20, 0xE0, 0x04, 0x00, 0x00, 0x00, 0x06]
_FRAME2_MAGIC = [0x02, 0x20, 0xE0, 0x04]

_NANOEX_MASK = 0x04
_FEATURE_BASE = 0x02
_SHORT_FRAME_MARKER = 0x80


class PanasonicAcModel(StrEnum):
    """Panasonic 216-bit protocol variants; PKE includes the CS-NE9PKE."""

    DKE = "DKE"
    JKE = "JKE"
    LKE = "LKE"
    NKE = "NKE"
    CKP = "CKP"
    RKR = "RKR"
    PKE = "PKE"


class PanasonicAcMode(IntEnum):
    """Operation mode, stored in the high nibble of byte 13."""

    AUTO = 0x0
    DRY = 0x2
    COOL = 0x3
    HEAT = 0x4
    FAN_ONLY = 0x6


class PanasonicAcFanSpeed(IntEnum):
    """Fan speed, stored in the high nibble of byte 16."""

    AUTO = 0xA
    LOW = 0x3
    MEDIUM_LOW = 0x4
    MEDIUM = 0x5
    MEDIUM_HIGH = 0x6
    HIGH = 0x7


class PanasonicAcSwingAxis1(IntEnum):
    """Swing positions for protocol slot 1 (low nibble of byte 16).

    The physical louver this drives depends on the unit: on window units it is
    the (single) horizontal louver, while on split units it is the vertical
    louver. The position names follow the IRremoteESP8266 vertical-swing labels
    and are axis-relative, so the caller maps them to the real direction.
    """

    AUTO = 0xF
    HIGHEST = 0x1
    HIGH = 0x2
    MIDDLE = 0x3
    LOW = 0x4
    LOWEST = 0x5


class PanasonicAcSwingAxis2(IntEnum):
    """Swing positions for protocol slot 2 (low nibble of byte 17).

    On split units this is the horizontal louver; many units (e.g. single-louver
    window units) leave it at :attr:`AUTO`. The position names follow the
    IRremoteESP8266 horizontal-swing labels and are axis-relative.
    """

    AUTO = 0xD
    MIDDLE = 0x6
    FULL_LEFT = 0x9
    LEFT = 0xA
    RIGHT = 0xB
    FULL_RIGHT = 0xC


class PanasonicAcToggle(Enum):
    """Short-frame toggle command, holding its two payload bytes (13, 14)."""

    QUIET = (0x81, 0x33)
    POWERFUL = (0x86, 0x35)


@dataclass(frozen=True, kw_only=True)
class PanasonicAcState:
    """Decoded native Panasonic settings; CKP carries a power toggle."""

    mode: PanasonicAcMode
    temperature: float | None
    fan: PanasonicAcFanSpeed
    power: bool | None
    power_toggle: bool | None
    swing_axis1: PanasonicAcSwingAxis1
    swing_axis2: PanasonicAcSwingAxis2 | None
    frost_protection: bool
    nanoex: bool | None


def _checksum(state: list[int], start: int, end: int) -> int:
    """Sum bytes ``state[start..end]`` (inclusive) modulo 256."""
    return sum(state[start : end + 1]) & 0xFF


def _to_frames(state: list[int]) -> list[bytes]:
    """Split a full state byte list into Kaseikyo per-frame payloads.

    Each frame's first two bytes are the Kaseikyo address (``0x2002``), so the
    payload passed to :class:`KaseikyoCommand` is the state with those two
    address bytes dropped from each section.
    """
    return [bytes(state[2:8]), bytes(state[10:])]


class PanasonicAcCommand(KaseikyoCommand):
    """Panasonic air-conditioner full-state IR command."""

    def __init__(
        self,
        *,
        mode: PanasonicAcMode,
        temperature: float | None = None,
        model: PanasonicAcModel | None = None,
        fan: PanasonicAcFanSpeed = PanasonicAcFanSpeed.AUTO,
        power: bool | None = None,
        power_toggle: bool | None = None,
        swing_axis1: PanasonicAcSwingAxis1 = PanasonicAcSwingAxis1.AUTO,
        swing_axis2: PanasonicAcSwingAxis2 | None = None,
        nanoex: bool = False,
        frost_protection: bool = False,
        modulation: int | None = None,
    ) -> None:
        """Build a full Panasonic A/C state command.

        ``temperature`` must be 16..30 °C. Named models use whole degrees;
        omitting ``model`` preserves the original half-degree encoding.

        ``power`` defaults to on. CKP instead requires ``power_toggle``: True
        toggles power, False leaves it unchanged. The caller tracks CKP state.

        ``frost_protection`` requires a named model and HEAT mode, and sends
        10 °C with maximum fan and automatic vane position. Fan-only sends
        27 °C. Neither changes the caller's remembered temperature set point.

        Named models default to 36.7 kHz with 432 us bit marks. Only DKE and RKR
        expose axis 2; their default is middle. nanoeX belongs to the original
        layout and is not supported for named models.
        """
        if temperature is not None and not MIN_TEMP <= temperature <= MAX_TEMP:
            raise ValueError(
                f"temperature {temperature} out of range {MIN_TEMP}..{MAX_TEMP}"
            )

        if model is not None and temperature is not None and temperature % 1:
            raise ValueError("temperature must be a whole degree for named models")
        if model == PanasonicAcModel.CKP:
            if power is not None or power_toggle is None:
                raise ValueError("CKP requires power_toggle instead of power")
            power_bit = power_toggle
        else:
            if power_toggle is not None:
                raise ValueError("power_toggle is only supported for CKP")
            power_bit = True if power is None else power

        if frost_protection:
            if model is None or mode != PanasonicAcMode.HEAT:
                raise ValueError(
                    "frost_protection requires a named model and HEAT mode"
                )
            temperature = 10
            fan = PanasonicAcFanSpeed.HIGH
            swing_axis1 = PanasonicAcSwingAxis1.AUTO
        elif mode == PanasonicAcMode.FAN_ONLY:
            temperature = 27

        if temperature is None:
            raise ValueError("temperature is required for this mode")

        axis2: int = PanasonicAcSwingAxis2.AUTO if swing_axis2 is None else swing_axis2
        mode_flags = 0
        byte21 = 0
        byte23 = 0x81
        byte25 = _FEATURE_BASE | (_NANOEX_MASK if nanoex else 0x00)
        if model is not None:
            if nanoex:
                raise ValueError("nanoex is not supported for named models")
            if model in (PanasonicAcModel.DKE, PanasonicAcModel.RKR):
                axis2 = (
                    PanasonicAcSwingAxis2.MIDDLE if swing_axis2 is None else swing_axis2
                )
            else:
                if swing_axis2 is not None:
                    raise ValueError(f"swing_axis2 is not supported for {model}")
                axis2 = (
                    0x06
                    if model in (PanasonicAcModel.LKE, PanasonicAcModel.NKE)
                    else 0x00
                )
            if model == PanasonicAcModel.LKE:
                mode_flags = 0x02
            elif model in (PanasonicAcModel.RKR, PanasonicAcModel.PKE):
                mode_flags = 0x08
            if model == PanasonicAcModel.CKP:
                byte21 = 0x10
            if model in (PanasonicAcModel.DKE, PanasonicAcModel.CKP):
                byte23 = 0x01
            elif model == PanasonicAcModel.RKR:
                byte23 = 0x89
            byte25 = 0x06 if model == PanasonicAcModel.DKE else 0x00

        state = [
            *_FRAME1,
            *_FRAME2_MAGIC,
            0x00,
            (mode << 4) | mode_flags | int(power_bit),
            round(temperature * 2),
            0x80,
            (fan << 4) | swing_axis1,
            axis2,
            0x00,
            0x0E,
            0xE0,
            byte21,
            0x00,
            byte23,
            0x00,
            byte25,
        ]
        state.append(_checksum(state, 8, 25))

        super().__init__(
            address=PANASONIC_AC_ADDRESS,
            data=_to_frames(state),
            modulation=(
                modulation
                if modulation is not None
                else 38000
                if model is None
                else 36700
            ),
        )
        self.model = model
        if model is not None:
            # The recorded pulse durations are independent of carrier frequency.
            self.base_unit = 432

    @property
    def state(self) -> PanasonicAcState:
        """Recover settings without replacing the retained received bytes."""
        payload = self.data[-1] if isinstance(self.data, list) else self.data
        frame = bytes([2, 32]) + payload
        mode = PanasonicAcMode(frame[5] >> 4)
        temperature = frame[6] / 2
        frost = mode == PanasonicAcMode.HEAT and temperature in (8, 10)
        ckp = self.model == PanasonicAcModel.CKP
        return PanasonicAcState(
            mode=mode,
            temperature=None
            if frost or mode == PanasonicAcMode.FAN_ONLY
            else temperature,
            fan=PanasonicAcFanSpeed(frame[8] >> 4),
            power=None if ckp else bool(frame[5] & 1),
            power_toggle=bool(frame[5] & 1) if ckp else None,
            swing_axis1=PanasonicAcSwingAxis1(frame[8] & 15),
            swing_axis2=PanasonicAcSwingAxis2(frame[9] & 15)
            if self.model in (None, PanasonicAcModel.DKE, PanasonicAcModel.RKR)
            else None,
            frost_protection=frost,
            nanoex=bool(frame[17] & 4) if self.model is None else None,
        )

    @classmethod
    def from_raw_timings(
        cls, timings: list[int], *, model: PanasonicAcModel | None = None
    ) -> Self | None:
        """Decode the state section alone or both frames, checking their checksums.

        Supply the configured model to interpret variant fields. CKP's power bit
        remains a toggle; a receiver cannot recover absolute power from it.
        The received payloads are retained so reserved bytes survive re-encoding.
        """
        decoded = KaseikyoCommand.from_raw_timings(timings)
        if decoded is None or decoded.address != PANASONIC_AC_ADDRESS:
            return None
        if isinstance(decoded.data, bytes):
            first, second = bytes(_FRAME1), bytes([2, 32]) + decoded.data
        elif len(decoded.data) == 2:
            first, second = (bytes([2, 32]) + frame for frame in decoded.data)
        else:
            return None
        if (
            first != bytes(_FRAME1)
            or len(second) != 19
            or second[:5] != bytes([2, 32, 0xE0, 4, 0])
            or sum(second[:-1]) & 255 != second[-1]
        ):
            return None
        try:
            mode = PanasonicAcMode(second[5] >> 4)
            fan = PanasonicAcFanSpeed(second[8] >> 4)
            swing = PanasonicAcSwingAxis1(second[8] & 15)
            temperature = second[6] / 2
            frost = (
                temperature in (8, 10)
                and model is not None
                and mode == PanasonicAcMode.HEAT
            )
            if not frost and not MIN_TEMP <= temperature <= MAX_TEMP:
                return None
            power_bit = bool(second[5] & 1)
            result = cls(
                mode=mode,
                temperature=16 if frost else temperature,
                model=model,
                fan=fan,
                power=None if model == PanasonicAcModel.CKP else power_bit,
                power_toggle=power_bit if model == PanasonicAcModel.CKP else None,
                swing_axis1=swing,
                swing_axis2=PanasonicAcSwingAxis2(second[9] & 15)
                if model is None
                or model in (PanasonicAcModel.DKE, PanasonicAcModel.RKR)
                else None,
                nanoex=bool(second[17] & 4) if model is None else False,
                frost_protection=frost,
            )
            result.data = [first[2:], second[2:]]
            result.base_unit = decoded.base_unit
            result.repeat_count = decoded.repeat_count
            result.full_frame_repeat = decoded.full_frame_repeat
            result._frame_gaps = decoded._frame_gaps or [10000]
            return result
        except ValueError:
            return None


class PanasonicAcToggleCommand(KaseikyoCommand):
    """Panasonic air-conditioner short toggle command (Quiet / Powerful)."""

    def __init__(
        self,
        *,
        toggle: PanasonicAcToggle,
        modulation: int = 38000,
    ) -> None:
        """Build a short Quiet/Powerful toggle command.

        These are dedicated 16-byte frames that carry no mode/temperature/fan/
        swing state; the unit keeps whatever it was already running.
        """
        state = [
            *_FRAME1,
            *_FRAME2_MAGIC,
            _SHORT_FRAME_MARKER,
            *toggle.value,
        ]
        state.append(_checksum(state, 8, 14))

        super().__init__(
            address=PANASONIC_AC_ADDRESS,
            data=_to_frames(state),
            modulation=modulation,
        )

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode the Quiet/Powerful action section alone or both checked sections."""
        decoded = KaseikyoCommand.from_raw_timings(timings)
        if decoded is None or decoded.address != PANASONIC_AC_ADDRESS:
            return None
        if isinstance(decoded.data, bytes):
            first, second = bytes(_FRAME1), bytes([2, 32]) + decoded.data
        elif len(decoded.data) == 2:
            first, second = (bytes([2, 32]) + frame for frame in decoded.data)
        else:
            return None
        if (
            first != bytes(_FRAME1)
            or len(second) != 8
            or second[:5] != bytes([2, 32, 0xE0, 4, 128])
            or sum(second[:-1]) & 255 != second[-1]
        ):
            return None
        try:
            toggle = PanasonicAcToggle((second[5], second[6]))
        except ValueError:
            return None
        result = cls(toggle=toggle)
        result.data, result.base_unit = [first[2:], second[2:]], decoded.base_unit
        result.repeat_count = decoded.repeat_count
        result.full_frame_repeat = decoded.full_frame_repeat
        result._frame_gaps = decoded._frame_gaps or [10000]
        return result

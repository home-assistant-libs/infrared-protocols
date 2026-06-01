"""Panasonic air-conditioner IR protocol for Hong Kong / Macau models.

Reverse-engineered protocol for Panasonic air conditioners sold in Hong Kong
and Macau (CW-HU / CW-HZ / CW-SU / CW-SUL families). Builds a 27-byte full
state frame (power/mode/temperature/fan/swing/nanoeX) or a 16-byte
Quiet/Powerful short frame, then reuses the generic
:class:`~infrared_protocols.commands.panasonic_ac.PanasonicAcCommand` framing to
encode it to signed microsecond timings at 38 kHz.
"""

from typing import Literal, Self

from .panasonic_ac import PanasonicAcCommand, checksum

MIN_TEMP = 16
MAX_TEMP = 30

AcMode = Literal["auto", "dry", "cool", "heat"]
FanSpeed = Literal["auto", "low", "mediumLow", "medium", "mediumHigh", "high"]
SwingMode = Literal["auto", "fixed"]
ShortFrameKind = Literal["quiet", "powerful"]

_MODE_NIBBLE: dict[AcMode, int] = {
    "auto": 0x0,
    "dry": 0x2,
    "cool": 0x3,
    "heat": 0x4,
}
_FAN_NIBBLE: dict[FanSpeed, int] = {
    "auto": 0xA,
    "low": 0x3,
    "mediumLow": 0x4,
    "medium": 0x5,
    "mediumHigh": 0x6,
    "high": 0x7,
}
_SWING_NIBBLE: dict[SwingMode, int] = {"auto": 0xF, "fixed": 0x5}

_NANOEX_MASK = 0x04

_SHORT_PAYLOAD: dict[ShortFrameKind, list[int]] = {
    "quiet": [0x80, 0x81, 0x33],
    "powerful": [0x80, 0x86, 0x35],
}


def build_full_frame(
    *,
    off: bool = False,
    mode: AcMode,
    temp: float,
    fan: FanSpeed,
    swing: SwingMode,
    nanoex: bool,
) -> list[int]:
    """Build the 27-byte full state frame from semantic parameters.

    ``temp`` is in degrees Celsius; byte 14 stores ``round(temp * 2)`` so the
    protocol's 0.5 °C step is preserved.
    """
    state = [0] * 27
    for i, value in enumerate([0x02, 0x20, 0xE0, 0x04, 0x00, 0x00, 0x00, 0x06]):
        state[i] = value
    state[8] = 0x02
    state[9] = 0x20
    state[10] = 0xE0
    state[11] = 0x04
    state[12] = 0x00
    state[13] = (_MODE_NIBBLE[mode] << 4) | (0 if off else 1)
    state[14] = round(temp * 2)
    state[15] = 0x80
    state[16] = (_FAN_NIBBLE[fan] << 4) | _SWING_NIBBLE[swing]
    state[17] = 0x0D
    state[18] = 0x00
    state[19] = 0x0E
    state[20] = 0xE0
    state[21] = 0x00
    state[22] = 0x00
    state[23] = 0x81
    state[24] = 0x00
    state[25] = 0x02 | (_NANOEX_MASK if nanoex else 0x00)
    state[26] = checksum(state, 8, 25)
    return state


def build_short_frame(kind: ShortFrameKind) -> list[int]:
    """Build the 16-byte Quiet/Powerful toggle frame."""
    try:
        payload = _SHORT_PAYLOAD[kind]
    except KeyError:
        raise ValueError(f"unknown short-frame kind: {kind!r}") from None
    state = [
        0x02,
        0x20,
        0xE0,
        0x04,
        0x00,
        0x00,
        0x00,
        0x06,
        0x02,
        0x20,
        0xE0,
        0x04,
        *payload,
    ]
    state.append(checksum(state, 8, 14))
    return state


class PanasonicAcHkCommand(PanasonicAcCommand):
    """Panasonic air-conditioner IR command for Hong Kong / Macau models."""

    @classmethod
    def full(
        cls,
        *,
        off: bool = False,
        mode: AcMode,
        temp: float,
        fan: FanSpeed,
        swing: SwingMode,
        nanoex: bool,
    ) -> Self:
        """Build a full state command (power/mode/temp/fan/swing/nanoeX)."""
        return cls(
            state=build_full_frame(
                off=off,
                mode=mode,
                temp=temp,
                fan=fan,
                swing=swing,
                nanoex=nanoex,
            )
        )

    @classmethod
    def short(cls, *, kind: ShortFrameKind) -> Self:
        """Build a Quiet/Powerful toggle command."""
        return cls(state=build_short_frame(kind))

"""Panasonic air-conditioner IR protocol.

Panasonic A/C remotes use the Kaseikyo (AEHA) format with the Panasonic vendor
address ``0x2002``. The state is sent as two Kaseikyo frames (a fixed 8-byte
preamble frame followed by a 19-byte payload frame) separated by an inter-frame
gap, so this module builds the state bytes and delegates the physical-layer
encoding to :class:`~infrared_protocols.commands.kaseikyo.KaseikyoCommand`.

The encoder is intentionally generic rather than tied to one regional model: it
exposes the full field set (power, mode, temperature, fan, two swing axes and
nanoeX) so callers can drive whichever combination their unit supports.
"""

from enum import Enum, IntEnum

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


class PanasonicAcMode(IntEnum):
    """Operation mode, stored in the high nibble of byte 13."""

    AUTO = 0x0
    DRY = 0x2
    COOL = 0x3
    HEAT = 0x4


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
        temperature: float,
        fan: PanasonicAcFanSpeed = PanasonicAcFanSpeed.AUTO,
        power: bool = True,
        swing_axis1: PanasonicAcSwingAxis1 = PanasonicAcSwingAxis1.AUTO,
        swing_axis2: PanasonicAcSwingAxis2 = PanasonicAcSwingAxis2.AUTO,
        nanoex: bool = False,
        modulation: int = 38000,
    ) -> None:
        """Build a full Panasonic A/C state command.

        ``temperature`` is in degrees Celsius and is stored as ``round(°C × 2)``
        in byte 14, preserving the protocol's 0.5 °C step. It must be within
        :data:`MIN_TEMP`..:data:`MAX_TEMP`.
        """
        if not MIN_TEMP <= temperature <= MAX_TEMP:
            raise ValueError(
                f"temperature {temperature} out of range {MIN_TEMP}..{MAX_TEMP}"
            )

        state = [
            *_FRAME1,
            *_FRAME2_MAGIC,
            0x00,
            (mode << 4) | (0x01 if power else 0x00),
            round(temperature * 2),
            0x80,
            (fan << 4) | swing_axis1,
            swing_axis2,
            0x00,
            0x0E,
            0xE0,
            0x00,
            0x00,
            0x81,
            0x00,
            _FEATURE_BASE | (_NANOEX_MASK if nanoex else 0x00),
        ]
        state.append(_checksum(state, 8, 25))

        super().__init__(
            address=PANASONIC_AC_ADDRESS,
            data=_to_frames(state),
            modulation=modulation,
        )


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

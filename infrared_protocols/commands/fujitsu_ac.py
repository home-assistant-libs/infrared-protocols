"""Fujitsu General air-conditioner IR protocol.

Carried over the AEHA physical layer. The first six bytes are common to all messages
and end with a type byte that selects the layout of the rest:

  bytes 0-4: 0x14 0x63 0x00 0x10 0x10 signature, except for byte 2 bits 4-5, which
             hold the remote id and vary between remotes
  byte 5:    message type

A state message (type 0xFE) is 16 bytes and carries the whole unit state as a
bitfield:

  byte 6:       number of bytes following it, 0x09 for a state message
  byte 7:       protocol, which says how to read the temperature field
  byte 8:       temperature << 2 | fahrenheit << 1 | power
  byte 9:       timer type << 4 | clean << 3 | mode
  byte 10:      swing << 4 | fan
  bytes 11-13:  on and off timers
  byte 14:      outside quiet << 7 | filter << 3, with bit 5 always set
  byte 15:      checksum, the two's complement of bytes 7-14

Every other message with this layout is a 7-byte util message: the common header plus
a checksum byte holding the one's complement of the type byte. Those carry no state,
so this module only recognises them well enough to keep them out of the state decoder.

The 16-byte state message is the only state layout handled here. AR-DB1 and AR-JW2
remotes send a 15-byte one with its own type byte and its own checksum; those frames
are not encoded and do not decode.

A remote sets the power bit only while the unit is off, and sends the same frame with
the bit clear once it is running.
"""

from dataclasses import dataclass
from enum import IntEnum
from typing import ClassVar, Self

from .aeha import AehaCommand, AehaTiming

MIN_TEMP = 16.0
MAX_TEMP = 30.0
MIN_TEMP_F = 60.0
MAX_TEMP_F = 88.0

_FUJITSU_TIMING = AehaTiming(
    leader_mark=3300,
    leader_space=1600,
    bit_mark=420,
    zero_space=420,
    one_space=1200,
)

_COMMON_SIGNATURE = (0x14, 0x63, 0x00, 0x10, 0x10)
# Masks out byte 2 bits 4-5, the remote id, which is not part of the signature.
_COMMON_SIGNATURE_MASK = (0xFF, 0xFF, 0xCF, 0xFF, 0xFF)
_COMMON_LENGTH = 6
_TYPE_BYTE = 5

MAX_DEVICE_ID = 3

_STATE_TYPE = 0xFE
_STATE_LENGTH = 16
_REST_LENGTH_BYTE = 6
_PROTOCOL_BYTE = 7
_CHECKSUM_FIRST_BYTE = 7

# Byte 14 holds the outside-quiet and filter flags, and bit 5 is set in every frame
_FLAGS_BYTE = 14
_FLAGS_BASE = 0x20
_OUTSIDE_QUIET_BIT = 0x80

# (byte, shift, mask) for each state field.
_DEVICE_ID = (2, 4, 0x03)
_FILTER = (14, 3, 0x01)
_POWER = (8, 0, 0x01)
_FAHRENHEIT = (8, 1, 0x01)
_TEMPERATURE = (8, 2, 0x3F)
_MODE = (9, 0, 0x07)
_CLEAN = (9, 3, 0x01)
_FAN = (10, 0, 0x07)
_SWING = (10, 4, 0x03)


class FujitsuAcProtocol(IntEnum):
    """Protocol byte at byte 7; says how to read the temperature field.

    Every frame names its own family here, and a unit reads the temperature field the
    way the frame says rather than the way its own remote would. The choice decides
    resolution: only :attr:`EXTENDED` can express a half degree or a Fahrenheit
    setpoint.
    """

    STANDARD = 0x30
    """1 C steps. ARRAH2E, ARREB1E, ARRY4 and similar remotes.

    ARDB1 and ARJW2 remotes scale the field the same way but wrap it in the 15-byte
    state message, which this module does not handle.
    """

    EXTENDED = 0x31
    """0.5 C steps, and a Fahrenheit setting. ARREW4E and similar remotes."""


class FujitsuAcMode(IntEnum):
    """AC operating mode; value is the protocol field at byte 9 bits 0-2."""

    AUTO = 0x00
    COOL = 0x01
    DRY = 0x02
    FAN_ONLY = 0x03
    HEAT = 0x04


class FujitsuAcFanSpeed(IntEnum):
    """Fan speed; value is the protocol field at byte 10 bits 0-2."""

    AUTO = 0x00
    HIGH = 0x01
    MEDIUM = 0x02
    LOW = 0x03
    QUIET = 0x04


class FujitsuAcSwing(IntEnum):
    """Louvre swing; value is the protocol field at byte 10 bits 4-5."""

    OFF = 0x00
    VERTICAL = 0x01
    HORIZONTAL = 0x02
    BOTH = 0x03


@dataclass(frozen=True, slots=True)
class _TemperatureScale:
    """How one protocol reads the 6-bit temperature field, in one unit."""

    offset: float
    """Degrees the field counts up from."""

    per_degree: int
    """Field counts per degree."""

    step: float
    """Smallest change a remote of this family sends."""

    minimum: float
    maximum: float


# The families scale the field differently and agree only at 24 C. STANDARD counts four
# per degree up from 16 C, so 16-30 C is field 0 to 56. Both EXTENDED scales span field
# 16 to 44 instead, which is 16-30 C or 60-88 F.
_TEMPERATURE_SCALES = {
    (FujitsuAcProtocol.STANDARD, False): _TemperatureScale(
        offset=16.0, per_degree=4, step=1.0, minimum=MIN_TEMP, maximum=MAX_TEMP
    ),
    (FujitsuAcProtocol.EXTENDED, False): _TemperatureScale(
        offset=8.0, per_degree=2, step=0.5, minimum=MIN_TEMP, maximum=MAX_TEMP
    ),
    (FujitsuAcProtocol.EXTENDED, True): _TemperatureScale(
        offset=44.0, per_degree=1, step=1.0, minimum=MIN_TEMP_F, maximum=MAX_TEMP_F
    ),
}


def _temperature_scale(
    protocol: FujitsuAcProtocol, *, is_fahrenheit: bool = False
) -> _TemperatureScale:
    """Return how a protocol reads its temperature field in the given unit."""
    scale = _TEMPERATURE_SCALES.get((protocol, is_fahrenheit))
    if scale is None:
        raise ValueError(f"{protocol.name} remotes have no Fahrenheit setting")
    return scale


def temperature_step(
    protocol: FujitsuAcProtocol, *, is_fahrenheit: bool = False
) -> float:
    """Return the smallest temperature change a protocol's remote can express."""
    return _temperature_scale(protocol, is_fahrenheit=is_fahrenheit).step


def _get_field(message: list[int], field: tuple[int, int, int]) -> int:
    """Read a (byte, shift, mask) bitfield from the message."""
    byte, shift, mask = field
    return (message[byte] >> shift) & mask


def _set_field(message: list[int], field: tuple[int, int, int], value: int) -> None:
    """Write a (byte, shift, mask) bitfield into the message."""
    byte, shift, mask = field
    message[byte] = (message[byte] & ~(mask << shift)) | ((value & mask) << shift)


def _encode_temperature(scale: _TemperatureScale, temperature: float) -> int:
    """Convert a temperature to its 6-bit field value."""
    return round((temperature - scale.offset) * scale.per_degree)


def _decode_temperature(scale: _TemperatureScale, field: int) -> float:
    """Convert a 6-bit field value back to a temperature."""
    return field / scale.per_degree + scale.offset


def _validate_temperature(scale: _TemperatureScale, temperature: float) -> None:
    """Reject a temperature the field cannot carry exactly."""
    if not scale.minimum <= temperature <= scale.maximum:
        raise ValueError(
            f"temperature {temperature} out of range {scale.minimum}..{scale.maximum}"
        )
    if temperature % scale.step:
        raise ValueError(f"temperature {temperature} is not a multiple of {scale.step}")


def _state_checksum(message: list[int]) -> int:
    """Return the state message checksum: the two's complement of bytes 7-14."""
    return -sum(message[_CHECKSUM_FIRST_BYTE : _STATE_LENGTH - 1]) & 0xFF


def _state_message(
    *,
    protocol: FujitsuAcProtocol,
    power: bool,
    mode: FujitsuAcMode,
    temperature: float,
    fan: FujitsuAcFanSpeed,
    swing: FujitsuAcSwing,
    clean: bool,
    filter: bool,
    outside_quiet: bool,
    is_fahrenheit: bool,
    device_id: int,
) -> bytes:
    """Build the state message for a full unit state."""
    message = [*_COMMON_SIGNATURE, _STATE_TYPE]
    message += [0] * (_STATE_LENGTH - len(message))
    message[_REST_LENGTH_BYTE] = _STATE_LENGTH - _REST_LENGTH_BYTE - 1
    message[_PROTOCOL_BYTE] = protocol.value
    message[_FLAGS_BYTE] = _FLAGS_BASE | (_OUTSIDE_QUIET_BIT if outside_quiet else 0)

    _set_field(message, _DEVICE_ID, device_id)
    _set_field(message, _FILTER, filter)
    _set_field(message, _POWER, power)
    _set_field(message, _FAHRENHEIT, is_fahrenheit)
    _set_field(
        message,
        _TEMPERATURE,
        _encode_temperature(
            _temperature_scale(protocol, is_fahrenheit=is_fahrenheit), temperature
        ),
    )
    _set_field(message, _MODE, mode.value)
    _set_field(message, _CLEAN, clean)
    _set_field(message, _FAN, fan.value)
    _set_field(message, _SWING, swing.value)

    message[_STATE_LENGTH - 1] = _state_checksum(message)
    return bytes(message)


class FujitsuAcCommand(AehaCommand):
    """Fujitsu General air-conditioner state IR command."""

    TIMING: ClassVar[AehaTiming] = _FUJITSU_TIMING

    protocol: FujitsuAcProtocol
    """Frame format, which need not match the remote the unit came with.

    See :class:`FujitsuAcProtocol` for what the choice decides.
    """

    power: bool
    """Whether this frame starts a unit that is currently off.

    Not an on/off switch: a remote sets it only while the unit is off, and a state
    message without it changes the settings of a running unit and leaves a stopped one
    stopped. Stopping a unit is a fixed code, not a state message.
    """

    mode: FujitsuAcMode
    temperature: float
    """Setpoint, in degrees Celsius unless :attr:`is_fahrenheit` is set."""

    is_fahrenheit: bool
    """Whether :attr:`temperature` is in degrees Fahrenheit.

    Only a :attr:`FujitsuAcProtocol.EXTENDED` remote can express it. Both units use
    the same field, so a unit reads whichever one this flag names.
    """

    fan: FujitsuAcFanSpeed
    swing: FujitsuAcSwing
    clean: bool
    """The clean function on most remotes.

    On a :attr:`FujitsuAcProtocol.EXTENDED` remote it is also how the 10 C
    minimum-heat function is sent, combined with :attr:`FujitsuAcMode.FAN_ONLY`.
    """

    filter: bool
    """The filter function, which only an ARRY4-family remote sends."""

    outside_quiet: bool

    device_id: int
    """Remote id carried in byte 2, 0 to :data:`MAX_DEVICE_ID`.

    A unit answers only the id it is set to, so several units can share a room. Every
    captured remote sends 0, which is the default here.
    """

    def __init__(
        self,
        *,
        temperature: float,
        protocol: FujitsuAcProtocol = FujitsuAcProtocol.STANDARD,
        power: bool = False,
        mode: FujitsuAcMode = FujitsuAcMode.AUTO,
        fan: FujitsuAcFanSpeed = FujitsuAcFanSpeed.AUTO,
        swing: FujitsuAcSwing = FujitsuAcSwing.OFF,
        clean: bool = False,
        filter: bool = False,
        outside_quiet: bool = False,
        is_fahrenheit: bool = False,
        device_id: int = 0,
        modulation: int = 38000,
    ) -> None:
        """Initialize the Fujitsu General AC state command."""
        _validate_temperature(
            _temperature_scale(protocol, is_fahrenheit=is_fahrenheit), temperature
        )
        if not 0 <= device_id <= MAX_DEVICE_ID:
            raise ValueError(f"device id {device_id} out of range 0..{MAX_DEVICE_ID}")

        self.protocol = protocol
        self.power = power
        self.mode = mode
        self.temperature = temperature
        self.is_fahrenheit = is_fahrenheit
        self.fan = fan
        self.swing = swing
        self.clean = clean
        self.filter = filter
        self.outside_quiet = outside_quiet
        self.device_id = device_id

        super().__init__(
            data=_state_message(
                protocol=protocol,
                power=power,
                mode=mode,
                temperature=temperature,
                fan=fan,
                swing=swing,
                clean=clean,
                filter=filter,
                outside_quiet=outside_quiet,
                is_fahrenheit=is_fahrenheit,
                device_id=device_id,
            ),
            modulation=modulation,
        )

    @classmethod
    def _common_message(cls, timings: list[int]) -> list[int] | None:
        """Decode timings into a message opening with the Fujitsu General signature."""
        data = cls._decode_data(timings)
        if data is None or len(data) < _COMMON_LENGTH:
            return None
        masked = tuple(
            byte & mask
            for byte, mask in zip(
                data[:_TYPE_BYTE], _COMMON_SIGNATURE_MASK, strict=True
            )
        )
        if masked != _COMMON_SIGNATURE:
            return None
        return list(data)

    @classmethod
    def from_raw_timings(cls, timings: list[int]) -> Self | None:
        """Decode raw IR timings into a :class:`FujitsuAcCommand`.

        Returns a :class:`FujitsuAcCommand` if the timings carry a state message, or
        None otherwise. A util message carries no state, so it decodes to None here.

        The timers are not modelled, so decoding is lossy: a frame that sets one yields
        the state it also carries, and re-encoding leaves the timer clear.
        """
        message = cls._common_message(timings)
        if message is None or message[_TYPE_BYTE] != _STATE_TYPE:
            return None
        if len(message) != _STATE_LENGTH:
            return None

        # Byte 6 is below the checksummed range, so it is the one field a corrupted
        # frame can change without the checksum noticing.
        if message[_REST_LENGTH_BYTE] != _STATE_LENGTH - _REST_LENGTH_BYTE - 1:
            return None
        if message[_STATE_LENGTH - 1] != _state_checksum(message):
            return None

        if not message[_FLAGS_BYTE] & _FLAGS_BASE:
            return None

        try:
            protocol = FujitsuAcProtocol(message[_PROTOCOL_BYTE])
            mode = FujitsuAcMode(_get_field(message, _MODE))
            fan = FujitsuAcFanSpeed(_get_field(message, _FAN))
            swing = FujitsuAcSwing(_get_field(message, _SWING))
        except ValueError:
            return None

        is_fahrenheit = bool(_get_field(message, _FAHRENHEIT))
        try:
            scale = _temperature_scale(protocol, is_fahrenheit=is_fahrenheit)
        except ValueError:
            return None

        temperature = _decode_temperature(scale, _get_field(message, _TEMPERATURE))
        try:
            # STANDARD counts four per degree but steps a whole one, so a field off
            # that grid decodes in range and still is not a temperature a remote sends.
            _validate_temperature(scale, temperature)
        except ValueError:
            return None

        return cls(
            protocol=protocol,
            power=bool(_get_field(message, _POWER)),
            mode=mode,
            temperature=temperature,
            is_fahrenheit=is_fahrenheit,
            fan=fan,
            swing=swing,
            clean=bool(_get_field(message, _CLEAN)),
            filter=bool(_get_field(message, _FILTER)),
            outside_quiet=bool(message[_FLAGS_BYTE] & _OUTSIDE_QUIET_BIT),
            device_id=_get_field(message, _DEVICE_ID),
        )

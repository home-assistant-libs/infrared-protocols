"""Tests for the Gree AC IR command encoder and decoder."""

from collections.abc import Callable

import pytest

from infrared_protocols.commands.gree_ac import (
    GreeAcAir,
    GreeAcFanSpeed,
    GreeAcMode,
    GreeAcSinclairCommand,
)

# Physical-layer constants are duplicated here rather than imported
# so the tests are independent
_MARK = 560
_ZERO = -560
_ONE = -1690

# power=True, mode=cool (0x01), temp=24, fan=auto (0x00), swing=False
# byte0 = mode 0x01 | power 0x08 | (fan 0x00 << 4) = 0x09
# byte1 = 24 - 16 = 0x08
# byte2 = 0x00
# byte3 = 0x50
_BASE_FRAME_TIMINGS = [
    # Header
    9000, -4500,
    # byte0 = 0x09: bits LSB first = 1,0,0,1,0,0,0,0 (bit0=mode cool, bit3=power)
    _MARK, _ONE,
    _MARK, _ZERO,
    _MARK, _ZERO,
    _MARK, _ONE,
    _MARK, _ZERO,
    _MARK, _ZERO,
    _MARK, _ZERO,
    _MARK, _ZERO,
    # byte1 = 0x08: bits LSB first = 0,0,0,1,0,0,0,0
    _MARK, _ZERO,
    _MARK, _ZERO,
    _MARK, _ZERO,
    _MARK, _ONE,
    _MARK, _ZERO,
    _MARK, _ZERO,
    _MARK, _ZERO,
    _MARK, _ZERO,
    # byte2 = 0x00: all zeros
    _MARK, _ZERO,
    _MARK, _ZERO,
    _MARK, _ZERO,
    _MARK, _ZERO,
    _MARK, _ZERO,
    _MARK, _ZERO,
    _MARK, _ZERO,
    _MARK, _ZERO,
    # byte3 = 0x50: bits LSB first = 0,0,0,0,1,0,1,0
    _MARK, _ZERO,
    _MARK, _ZERO,
    _MARK, _ZERO,
    _MARK, _ZERO,
    _MARK, _ONE,
    _MARK, _ZERO,
    _MARK, _ONE,
    _MARK, _ZERO,
    # 3-bit connector: 0, 1, 0
    _MARK, _ZERO,
    _MARK, _ONE,
    _MARK, _ZERO,
    # End mark
    _MARK,
]  # fmt: skip


def _space(bit: int) -> int:
    """Return the timing index of the space for frame data bit ``bit``."""
    return 3 + 2 * bit


_MODE_BIT0_SPACE = _space(0)
_POWER_SPACE = _space(3)
_SLEEP_SPACE = _space(7)
_TEMP_BIT0_SPACE = _space(8)
_AIR_BIT0_SPACE = _space(24)
_SIGNATURE_BIT0_SPACE = _space(26)


def _sinclair_command(
    *,
    power: bool = True,
    mode: GreeAcMode = GreeAcMode.COOL,
    temperature: int = 24,
    fan: GreeAcFanSpeed = GreeAcFanSpeed.AUTO,
    swing_v: bool = False,
    sleep: bool = False,
    timer_hours: float | None = None,
    humidity: bool = False,
    light: bool = False,
    anion: bool = False,
    save: bool = False,
    air: GreeAcAir = GreeAcAir.OFF,
) -> GreeAcSinclairCommand:
    """Build a representative Sinclair command."""
    return GreeAcSinclairCommand(
        power=power,
        mode=mode,
        temperature=temperature,
        fan=fan,
        swing_v=swing_v,
        sleep=sleep,
        timer_hours=timer_hours,
        humidity=humidity,
        light=light,
        anion=anion,
        save=save,
        air=air,
    )


def test_encode_frame_timings() -> None:
    """Pin the physical layer: carrier, single send, header, bits and the frame."""
    command = _sinclair_command()

    assert command.modulation == 38000
    assert command.repeat_count == 0
    assert command.get_raw_timings() == _BASE_FRAME_TIMINGS


def test_encode_power_off_clears_only_the_power_bit() -> None:
    """Powering off flips the power bit's space and leaves the rest untouched."""
    expected = list(_BASE_FRAME_TIMINGS)
    expected[_POWER_SPACE] = _ZERO

    assert _sinclair_command(power=False).get_raw_timings() == expected


@pytest.mark.parametrize(
    "command",
    [
        pytest.param(_sinclair_command(), id="defaults"),
        pytest.param(_sinclair_command(power=False), id="power_off"),
        pytest.param(_sinclair_command(mode=GreeAcMode.HEAT), id="mode"),
        pytest.param(_sinclair_command(temperature=16), id="temperature_min"),
        pytest.param(_sinclair_command(temperature=30), id="temperature_max"),
        pytest.param(_sinclair_command(fan=GreeAcFanSpeed.HIGH), id="fan"),
        pytest.param(_sinclair_command(swing_v=True), id="swing_v"),
        pytest.param(_sinclair_command(sleep=True), id="sleep"),
        pytest.param(_sinclair_command(timer_hours=5.5), id="timer"),
        pytest.param(_sinclair_command(humidity=True), id="humidity"),
        pytest.param(_sinclair_command(light=True), id="light"),
        pytest.param(_sinclair_command(anion=True), id="anion"),
        pytest.param(_sinclair_command(save=True), id="save"),
        pytest.param(_sinclair_command(air=GreeAcAir.LEVEL_2), id="air"),
        pytest.param(
            _sinclair_command(
                power=True,
                mode=GreeAcMode.HEAT,
                temperature=27,
                fan=GreeAcFanSpeed.MEDIUM,
                swing_v=True,
                sleep=True,
                timer_hours=23.5,
                humidity=True,
                light=True,
                anion=True,
                save=True,
                air=GreeAcAir.LEVEL_1,
            ),
            id="all_fields_combined",
        ),
    ],
)
def test_from_raw_timings_round_trips_every_field(
    command: GreeAcSinclairCommand,
) -> None:
    """Decoding an encoded frame reproduces every field."""
    decoded = GreeAcSinclairCommand.from_raw_timings(command.get_raw_timings())

    assert decoded is not None
    assert decoded.power == command.power
    assert decoded.mode == command.mode
    assert decoded.temperature == command.temperature
    assert decoded.fan == command.fan
    assert decoded.swing_v == command.swing_v
    assert decoded.sleep == command.sleep
    assert decoded.timer_hours == command.timer_hours
    assert decoded.humidity == command.humidity
    assert decoded.light == command.light
    assert decoded.anion == command.anion
    assert decoded.save == command.save
    assert decoded.air == command.air
    assert decoded.get_raw_timings() == command.get_raw_timings()


@pytest.mark.parametrize(
    ("power", "expected"),
    [
        pytest.param(True, True, id="power_on"),
        pytest.param(False, False, id="power_off"),
    ],
)
def test_from_raw_timings_distinguishes_power(power: bool, expected: bool) -> None:
    """The dedicated power bit (bit 3) decodes unambiguously."""
    decoded = GreeAcSinclairCommand.from_raw_timings(
        _sinclair_command(power=power).get_raw_timings()
    )

    assert decoded is not None
    assert decoded.power is expected


def test_from_raw_timings_rejects_short_input() -> None:
    """Timings shorter than a full frame return None."""
    assert GreeAcSinclairCommand.from_raw_timings([9000, -4500]) is None


@pytest.mark.parametrize(
    ("index", "value"),
    [
        pytest.param(0, 1000, id="header_mark_out_of_tolerance"),
        # Signature bit 26 must be 0.
        pytest.param(_SIGNATURE_BIT0_SPACE, _ONE, id="signature_mismatch"),
        # Setting temperature bit 8 turns offset 14 into 15 -> 31 C.
        pytest.param(_TEMP_BIT0_SPACE, _ONE, id="temperature_above_max"),
    ],
)
def test_from_raw_timings_rejects_invalid_frame(index: int, value: int) -> None:
    """A frame that fails header, signature or temperature validation returns None."""
    timings = list(_sinclair_command(temperature=30).get_raw_timings())
    timings[index] = value

    assert GreeAcSinclairCommand.from_raw_timings(timings) is None


@pytest.mark.parametrize(
    "mode_spaces",
    [
        pytest.param((_ONE, _ZERO, _ONE), id="mode_5"),
        pytest.param((_ZERO, _ONE, _ONE), id="mode_6"),
        pytest.param((_ONE, _ONE, _ONE), id="mode_7"),
    ],
)
def test_from_raw_timings_rejects_undefined_mode(
    mode_spaces: tuple[int, int, int],
) -> None:
    """The 3-bit mode field is wider than the modes the protocol defines."""
    timings = list(_sinclair_command().get_raw_timings())
    timings[_MODE_BIT0_SPACE : _MODE_BIT0_SPACE + 6 : 2] = mode_spaces

    assert GreeAcSinclairCommand.from_raw_timings(timings) is None


def test_from_raw_timings_rejects_undefined_air() -> None:
    """The 2-bit air field is wider than the levels the protocol defines."""
    timings = list(_sinclair_command().get_raw_timings())
    timings[_AIR_BIT0_SPACE] = _ONE
    timings[_AIR_BIT0_SPACE + 2] = _ONE

    assert GreeAcSinclairCommand.from_raw_timings(timings) is None


def test_timer_hours_off_the_half_hour_grid_raises() -> None:
    """The timer field only encodes whole and half hours."""
    with pytest.raises(ValueError, match="multiple of 0.5"):
        _sinclair_command(timer_hours=1.25)


@pytest.mark.parametrize(
    ("timer_hours", "set_bits"),
    [
        pytest.param(None, (12,), id="bits_set_while_timer_off"),
        pytest.param(5.0, (13, 14), id="hour_tens_above_2"),
        pytest.param(5.0, (17, 18, 19), id="hour_units_above_9"),
        pytest.param(5.0, (14,), id="duration_above_24_hours"),
    ],
)
def test_from_raw_timings_rejects_impossible_timer(
    timer_hours: float | None, set_bits: tuple[int, ...]
) -> None:
    """The timer splits the hour into decimal digits the remote cannot exceed."""
    timings = list(_sinclair_command(timer_hours=timer_hours).get_raw_timings())
    for bit in set_bits:
        timings[_space(bit)] = _ONE

    assert GreeAcSinclairCommand.from_raw_timings(timings) is None


def test_from_raw_timings_decodes_feature_bit() -> None:
    """A feature bit set in the raw frame decodes to the matching field."""
    timings = list(_sinclair_command().get_raw_timings())
    timings[_SLEEP_SPACE] = _ONE

    decoded = GreeAcSinclairCommand.from_raw_timings(timings)

    assert decoded is not None
    assert decoded.sleep is True


@pytest.mark.parametrize(
    "build",
    [
        pytest.param(
            lambda: _sinclair_command(temperature=15), id="temperature_below_min"
        ),
        pytest.param(
            lambda: _sinclair_command(temperature=31), id="temperature_above_max"
        ),
        pytest.param(lambda: _sinclair_command(timer_hours=-0.5), id="timer_below_min"),
        pytest.param(lambda: _sinclair_command(timer_hours=24.5), id="timer_above_max"),
    ],
)
def test_out_of_range_raises(build: Callable[[], GreeAcSinclairCommand]) -> None:
    """A value outside its frame slot is rejected instead of being truncated."""
    with pytest.raises(ValueError, match="out of range"):
        build()

"""Tests for daikin arc protocol behavior."""

import pytest

from infrared_protocols.commands._timing import byte_bits
from infrared_protocols.commands.daikin_ac import DaikinAcFanSpeed
from infrared_protocols.commands.daikin_arc import (
    DaikinAcMode,
    DaikinArcCommand,
    DaikinArcQueryCommand,
    DaikinArcSensorResponse,
    DaikinArcState,
    DaikinHumidity,
)


@pytest.mark.parametrize("humidity", list(DaikinHumidity))
@pytest.mark.parametrize("power", [True, False], ids=["on", "off"])
def test_arc_humidity(humidity: DaikinHumidity, power: bool) -> None:
    """All humidity selections survive both sections and their checksums."""
    sent = DaikinArcCommand(
        mode=DaikinAcMode.COOL,
        temperature=23,
        humidity=humidity,
        humidity_changed=True,
        power=power,
    )
    received = DaikinArcCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.humidity == humidity
    assert received.state.temperature == 23
    assert received.humidity_changed is power


def test_arc_query() -> None:
    """Sensor queries carry no inferred climate settings."""
    received = DaikinArcQueryCommand.from_raw_timings(
        DaikinArcQueryCommand().get_raw_timings()
    )
    assert received is not None
    assert received.data == bytes.fromhex("11da27008487203d")
    assert received.state == DaikinArcState()


@pytest.mark.parametrize(
    "known_bits,trailing",
    [
        pytest.param(191, [], id="missing-last-bit"),
        pytest.param(191, [-10000], id="trailing-idle"),
        pytest.param(192, [], id="complete"),
    ],
)
def test_arc_sensor_reply(known_bits: int, trailing: list[int]) -> None:
    """The response example records 26 C indoors without a known checksum."""
    # ESPHome components/daikin_arc/daikin_arc.cpp, sensor-response packet example.
    data = bytes.fromhex("11da2700001a0c042c21610700070c0018000e3c006c1b61")
    raw = [
        3450,
        -1760,
        *DaikinArcCommand.TIMING.encode(byte_bits(data)[:known_bits]),
        400,
        *trailing,
    ]
    received = DaikinArcSensorResponse.from_raw_timings(raw)
    assert received is not None
    assert received.data == data
    assert received.inside_temperature == 26
    assert received.known_bits == known_bits
    assert DaikinArcSensorResponse.from_raw_timings(raw[:-8]) is None


@pytest.mark.parametrize("mode", list(DaikinAcMode))
def test_arc_off_setpoint(mode: DaikinAcMode) -> None:
    """The off command carries 25 C even when it equals the fan-only sentinel."""
    sent = DaikinArcCommand(mode=mode, temperature=25, power=False)
    received = DaikinArcCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.state.temperature == 25


@pytest.mark.parametrize("fan", list(DaikinAcFanSpeed))
def test_arc_native_fan_levels(fan: DaikinAcFanSpeed) -> None:
    """Every native speed retains its type and can be sent back unchanged."""
    sent = DaikinArcCommand(mode=DaikinAcMode.COOL, temperature=24, fan=fan)
    received = DaikinArcCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.state.fan is fan
    assert received.data[28] >> 4 == int(fan)


@pytest.mark.parametrize(
    "mode",
    [
        pytest.param(DaikinAcMode.DRY, id="dry"),
        pytest.param(DaikinAcMode.FAN_ONLY, id="fan_only"),
        pytest.param(DaikinAcMode.AUTO, id="auto"),
    ],
)
def test_rebuild_absent_setpoint(mode: DaikinAcMode) -> None:
    """Modes with fixed wire temperatures can be rebuilt without inventing a target."""
    command = DaikinArcCommand(mode=mode)
    received = DaikinArcCommand.from_raw_timings(command.get_raw_timings())
    assert received is not None
    assert received.state.mode is not None
    assert received.state.temperature is None
    rebuilt = DaikinArcCommand(
        mode=received.state.mode, temperature=received.state.temperature
    )
    assert rebuilt.data == command.data


@pytest.mark.parametrize(
    "power", [pytest.param(True, id="on"), pytest.param(False, id="off")]
)
def test_required_setpoint(power: bool) -> None:
    """Frames that carry a set point require one explicitly."""
    with pytest.raises(ValueError, match="temperature is required"):
        DaikinArcCommand(mode=DaikinAcMode.COOL, power=power)

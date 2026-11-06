"""Tests for daikin arc protocol behavior."""

import pytest

from infrared_protocols.commands._timing import byte_bits
from infrared_protocols.commands.climate import ClimateMode, ClimateState
from infrared_protocols.commands.daikin_ac import DaikinAcFanSpeed
from infrared_protocols.commands.daikin_arc import (
    DaikinArcCommand,
    DaikinArcQueryCommand,
    DaikinArcSensorResponse,
    DaikinHumidity,
)


@pytest.mark.parametrize("humidity", list(DaikinHumidity))
@pytest.mark.parametrize("power", [True, False], ids=["on", "off"])
def test_arc_humidity(humidity: DaikinHumidity, power: bool) -> None:
    """All humidity selections survive both sections and their checksums."""
    sent = DaikinArcCommand(
        mode=ClimateMode.COOL,
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
    assert received.state == ClimateState()


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


@pytest.mark.parametrize("mode", list(ClimateMode))
def test_arc_off_setpoint(mode: ClimateMode) -> None:
    """The off command carries 25 C even when it equals the fan-only sentinel."""
    sent = DaikinArcCommand(mode=mode, temperature=25, power=False)
    received = DaikinArcCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.state.temperature == 25


@pytest.mark.parametrize("fan", list(DaikinAcFanSpeed))
def test_arc_native_fan_levels(fan: DaikinAcFanSpeed) -> None:
    """Every native speed retains its type and can be sent back unchanged."""
    sent = DaikinArcCommand(mode=ClimateMode.COOL, temperature=24, fan=fan)
    received = DaikinArcCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.fan is fan
    assert received.state.fan is fan
    assert received.data[28] >> 4 == int(fan)

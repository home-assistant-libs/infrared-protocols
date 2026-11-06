"""Semantic regressions and boundary values for the added climate families."""

import pytest

from infrared_protocols.commands._climate import ClimatePacket
from infrared_protocols.commands._timing import byte_bits
from infrared_protocols.commands.airton import AirtonCommand
from infrared_protocols.commands.ballu import BalluCommand
from infrared_protocols.commands.climate import ClimateFan, ClimateMode, ClimateState
from infrared_protocols.commands.daikin_arc import (
    DaikinArcCommand,
    DaikinArcQueryCommand,
    DaikinArcSensorResponse,
    DaikinHumidity,
)
from infrared_protocols.commands.daikin_brc import (
    DaikinBrcCommand,
    DaikinBrcFahrenheitCommand,
)
from infrared_protocols.commands.delonghi import DelonghiCommand
from infrared_protocols.commands.friedrich import FriedrichCommand
from infrared_protocols.commands.haier import HaierCommand
from infrared_protocols.commands.haier_tundra import (
    HaierButton,
    HaierTundraCommand,
    HaierUnit,
)
from infrared_protocols.commands.hitachi import (
    HitachiAc344Command,
    HitachiAc424Command,
    HitachiButton,
)
from infrared_protocols.commands.islandaire import IslandaireCommand
from infrared_protocols.commands.mistral import MistralCommand
from infrared_protocols.commands.mitsubishi import (
    MitsubishiCommand,
    MitsubishiFan,
    MitsubishiPreset,
)
from infrared_protocols.commands.pd_pioneer_climate import PdPioneerClimateCommand
from infrared_protocols.commands.pioneer_wyt import PioneerWytCommand
from infrared_protocols.commands.tcl112 import Tcl112Command
from infrared_protocols.commands.whirlpool import (
    HisenseArgCommand,
    WhirlpoolCommand,
    WhirlpoolDg11j191Command,
)
from infrared_protocols.commands.whynter import WhynterCommand
from infrared_protocols.commands.zhlt01 import Zhlt01Command


@pytest.mark.parametrize(
    "command",
    [
        pytest.param(
            BalluCommand(mode=ClimateMode.HEAT, temperature=23, power=False), id="ballu"
        ),
        pytest.param(
            DaikinArcCommand(mode=ClimateMode.FAN_ONLY, temperature=18, power=False),
            id="arc",
        ),
        pytest.param(
            DaikinBrcCommand(mode=ClimateMode.COOL, temperature=23, power=False),
            id="brc",
        ),
        pytest.param(
            DelonghiCommand(mode=ClimateMode.HEAT, temperature=23, power=False),
            id="delonghi",
        ),
        pytest.param(
            HaierTundraCommand(mode=ClimateMode.HEAT, temperature=23, power=False),
            id="haier",
        ),
        pytest.param(
            IslandaireCommand(mode=ClimateMode.HEAT, temperature_f=72, power=False),
            id="islandaire",
        ),
        pytest.param(
            MistralCommand(mode=ClimateMode.HEAT, temperature=23, power=False),
            id="mistral",
        ),
        pytest.param(
            Zhlt01Command(mode=ClimateMode.HEAT, temperature=23, power=False), id="zhlt"
        ),
        pytest.param(
            WhirlpoolCommand(mode=ClimateMode.COOL, temperature=24, off_command=True),
            id="whirlpool",
        ),
    ],
)
def test_off_has_no_placeholder_mode(command: ClimatePacket) -> None:
    """Off frames must not turn zeroed mode bits into a reported operating mode."""
    received = type(command).from_raw_timings(command.get_raw_timings())
    assert received is not None
    assert received.state.mode is None


@pytest.mark.parametrize(
    "command",
    [
        pytest.param(AirtonCommand(mode=ClimateMode.COOL, temperature=24), id="airton"),
        pytest.param(
            HitachiAc344Command(mode=ClimateMode.COOL, temperature=24), id="hitachi344"
        ),
        pytest.param(
            HitachiAc424Command(mode=ClimateMode.COOL, temperature=24), id="hitachi424"
        ),
    ],
)
def test_receiver_idle_shorter_than_sender_gap(command: ClimatePacket) -> None:
    """A receiver timeout can end the capture before the transmitter's next frame."""
    received = type(command).from_raw_timings(command.get_raw_timings()[:-1] + [-20000])
    assert received is not None
    assert received.state.mode == ClimateMode.COOL
    assert received.state.temperature == 24


@pytest.mark.parametrize("humidity", list(DaikinHumidity))
def test_arc_humidity(humidity: DaikinHumidity) -> None:
    """All humidity selections survive both sections and their checksums."""
    sent = DaikinArcCommand(
        mode=ClimateMode.COOL, temperature=23, humidity=humidity, humidity_changed=True
    )
    received = DaikinArcCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.humidity == humidity
    assert received.state.temperature == 23
    assert received.data[9] == 0x13


def test_arc_query() -> None:
    """Sensor queries carry no inferred climate settings."""
    received = DaikinArcQueryCommand.from_raw_timings(
        DaikinArcQueryCommand().get_raw_timings()
    )
    assert received is not None
    assert received.data == bytes.fromhex("11da27008487203d")
    assert received.state == ClimateState()


def test_arc_sensor_reply() -> None:
    """The response example records 26 C indoors without a known checksum."""
    # ESPHome components/daikin_arc/daikin_arc.cpp, sensor-response packet example.
    data = bytes.fromhex("11da2700001a0c042c21610700070c0018000e3c006c1b61")
    raw = [3450, -1760, *DaikinArcCommand.TIMING.encode(byte_bits(data)), 400]
    received = DaikinArcSensorResponse.from_raw_timings(raw)
    assert received is not None
    assert received.data == data
    assert received.inside_temperature == 26
    assert DaikinArcSensorResponse.from_raw_timings(raw[:-8]) is None


@pytest.mark.parametrize("sub_unit", [0, 1])
@pytest.mark.parametrize("mode_button", [False, True])
def test_brc_fahrenheit(sub_unit: int, mode_button: bool) -> None:
    """The constructor uses native Fahrenheit; common state exposes exact Celsius."""
    sent = DaikinBrcFahrenheitCommand(
        mode=ClimateMode.COOL,
        temperature=72,
        sub_unit=sub_unit,
        mode_button=mode_button,
    )
    received = DaikinBrcFahrenheitCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.state.temperature == pytest.approx(22.222222)
    assert received.sub_unit == sub_unit
    assert received.mode_button == mode_button


@pytest.mark.parametrize("fan", list(MitsubishiFan))
@pytest.mark.parametrize("temperature", [16, 16.5, 30.5, 31])
def test_mitsubishi_native_fields(fan: MitsubishiFan, temperature: float) -> None:
    """Intermediate speeds, both vanes and half degrees remain observable."""
    sent = MitsubishiCommand(
        mode=ClimateMode.COOL,
        temperature=temperature,
        fan=fan,
        preset=MitsubishiPreset.ECONO_COOL,
        vertical_position=3,
        horizontal_position=5,
        dual_vanes=True,
    )
    received = MitsubishiCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.fan == fan
    assert received.state.fan is not None
    assert received.state.temperature == temperature
    assert received.preset == MitsubishiPreset.ECONO_COOL
    assert received.vertical_position == 3
    assert received.horizontal_position == 5
    assert received.dual_vanes


@pytest.mark.parametrize("button", list(HaierButton))
@pytest.mark.parametrize("unit", list(HaierUnit))
def test_haier_buttons(button: HaierButton, unit: HaierUnit) -> None:
    """Each known action has a readable button and valid transport checksum."""
    sent = HaierTundraCommand(
        mode=ClimateMode.COOL,
        temperature=23,
        button=button,
        unit=unit,
        health=True,
        quiet=True,
    )
    received = HaierTundraCommand.from_raw_timings(sent.get_raw_timings())
    raw_packet = HaierCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert raw_packet is not None
    assert raw_packet.data == sent.data[:-1]
    assert (received.button, received.unit) == (button, unit)
    assert received.data[3] == 2
    assert received.data[6] == 128


@pytest.mark.parametrize("cls", [HaierTundraCommand, HitachiAc344Command])
def test_unknown_button_rejected(
    cls: type[HaierTundraCommand] | type[HitachiAc344Command],
) -> None:
    """A valid checksum cannot legitimize an unsupported action identifier."""
    with pytest.raises(ValueError):
        cls(mode=ClimateMode.COOL, temperature=24, button=255)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "cls,mode_code",
    [
        pytest.param(HitachiAc344Command, 7, id="344"),
        pytest.param(HitachiAc424Command, 14, id="424"),
    ],
)
def test_hitachi_receive_auto_maximum(
    cls: type[HitachiAc344Command], mode_code: int
) -> None:
    """Receive-only mode and speed codes remain explicit rather than rejected."""
    sent = cls(mode=ClimateMode.COOL, temperature=24)
    data = bytearray(sent.data)
    data[25] = 0x60 | mode_code
    data[26] = data[25] ^ 255
    sent.data = bytes(data)
    received = cls.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.state.mode == ClimateMode.AUTO
    assert received.state.fan == ClimateFan.MAXIMUM


def test_hitachi_mildew_and_quiet() -> None:
    """Mildew shutdown and quiet operation use distinct auxiliary bytes."""
    off = HitachiAc344Command(
        mode=ClimateMode.COOL,
        temperature=24,
        power=False,
        mildew_proof=True,
        button=HitachiButton.MILDEW_PROOF,
    )
    quiet = HitachiAc344Command(
        mode=ClimateMode.COOL, temperature=24, fan=ClimateFan.QUIET
    )
    assert off.data[9] == 0xA5
    assert quiet.data[9] == 0x98
    received = HitachiAc344Command.from_raw_timings(off.get_raw_timings())
    assert received is not None
    assert received.button == HitachiButton.MILDEW_PROOF
    assert received.state.power is False


@pytest.mark.parametrize("temperature", [16, 16.5, 24.5, 30.5, 31])
def test_tcl_half_degree(temperature: float) -> None:
    """The half-degree bit and quiet fan code are independent fields."""
    sent = Tcl112Command(
        mode=ClimateMode.COOL, temperature=temperature, fan=ClimateFan.QUIET
    )
    received = Tcl112Command.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.state.temperature == temperature
    assert received.state.fan == ClimateFan.QUIET


@pytest.mark.parametrize("temperature", [16, 16.5, 24.5, 30.5, 31])
def test_pd_half_degree_economy(temperature: float) -> None:
    """Both state bursts retain fractional targets and the economy flag."""
    sent = PdPioneerClimateCommand(
        mode=ClimateMode.COOL, temperature=temperature, economy=True
    )
    received = PdPioneerClimateCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.state.temperature == temperature
    assert received.economy


@pytest.mark.parametrize("packet_type", [0, 1, 2, 7, 255])
def test_wyt_application_types(packet_type: int) -> None:
    """Raw WYT accepts all application types and adds fifteen only for type two."""
    data = bytes([0x23, 0xCB, 0x26, packet_type, 0, 0x24, 3, 7, 5, 0x80, 0, 0, 0])
    sent = PioneerWytCommand(data=data)
    received = PioneerWytCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.data == data


def test_whirlpool_short_press() -> None:
    """A 14-byte press validates the first checksum without needing a third part."""
    sent = WhirlpoolCommand(mode=ClimateMode.COOL, temperature=24)
    sent.data = sent.data[:14]
    received = WhirlpoolCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert len(received.data) == 14
    assert received.state.mode == ClimateMode.COOL
    assert received.state.temperature == 24
    assert received.get_raw_timings() == sent.get_raw_timings()


@pytest.mark.parametrize(
    "cls,expected",
    [
        pytest.param(
            WhirlpoolDg11j191Command,
            "83060782000080000000000000050006000008000e",
            id="dg11j1-91",
        ),
        pytest.param(
            HisenseArgCommand,
            "830607820000800000000080189d00010000080009",
            id="hisense-arg",
        ),
    ],
)
def test_whirlpool_independent_packets(
    cls: type[WhirlpoolCommand], expected: str
) -> None:
    """ESPHome's whirlpool_tests.cpp records model-specific complete packets."""
    sent = cls(
        mode=ClimateMode.COOL, temperature=24, fan=ClimateFan.LOW, power_toggle=True
    )
    assert sent.data == bytes.fromhex(expected)
    received = cls.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.state.temperature == 24
    assert received.state.fan == ClimateFan.LOW
    assert received.power_toggle


def test_hisense_fan_sentinel() -> None:
    """Fan-only's fixed temperature nibble is not a set point."""
    sent = HisenseArgCommand(mode=ClimateMode.FAN_ONLY, temperature=24)
    assert sent.state.temperature is None


@pytest.mark.parametrize(
    "mode,temperature",
    [
        pytest.param(ClimateMode.HEAT, 60, id="heat-min"),
        pytest.param(ClimateMode.HEAT, 88, id="heat-max"),
        pytest.param(ClimateMode.COOL, 64, id="cool-min"),
        pytest.param(ClimateMode.COOL, 88, id="cool-max"),
    ],
)
def test_friedrich_economy_boundaries(mode: ClimateMode, temperature: int) -> None:
    """Native even-degree Fahrenheit endpoints and economy decode together."""
    sent = FriedrichCommand(mode=mode, temperature_f=temperature, economy=True)
    received = FriedrichCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.temperature_f == temperature
    assert received.state.temperature == pytest.approx((temperature - 32) * 5 / 9)
    assert received.economy


@pytest.mark.parametrize(
    "mode,temperature",
    [
        pytest.param(ClimateMode.HEAT, 13, id="heat-min"),
        pytest.param(ClimateMode.HEAT, 27, id="heat-max"),
        pytest.param(ClimateMode.COOL, 17, id="cool-min"),
        pytest.param(ClimateMode.COOL, 32, id="cool-max"),
    ],
)
def test_delonghi_temperature_ranges(mode: ClimateMode, temperature: int) -> None:
    """Heating and cooling use different offsets and valid endpoints."""
    sent = DelonghiCommand(mode=mode, temperature=temperature)
    received = DelonghiCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.state.mode == mode
    assert received.state.temperature == temperature


def test_whynter_fahrenheit() -> None:
    """Native Fahrenheit encoding is decoded to the shared Celsius state."""
    sent = WhynterCommand(mode=ClimateMode.COOL, temperature=75, fahrenheit=True)
    received = WhynterCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.state.temperature == pytest.approx((75 - 32) * 5 / 9)


def test_haier_unknown_received_button() -> None:
    """Reject unknown button values before exposing an accessor that would fail."""
    sent = HaierTundraCommand(mode=ClimateMode.COOL, temperature=24)
    data = bytearray(sent.data)
    data[12] = 0x14
    data[-1] = sum(data[:-1]) & 255
    sent.data = bytes(data)
    assert HaierTundraCommand.from_raw_timings(sent.get_raw_timings()) is None


def test_hitachi_unknown_received_button() -> None:
    """A correct complement cannot turn an unknown action into a known button."""
    sent = HitachiAc344Command(mode=ClimateMode.COOL, temperature=24)
    data = bytearray(sent.data)
    data[11], data[12] = 0x22, 0xDD
    sent.data = bytes(data)
    assert HitachiAc344Command.from_raw_timings(sent.get_raw_timings()) is None


def test_haier_turbo() -> None:
    """Turbo's auxiliary flag differs from quiet, and the two are exclusive."""
    sent = HaierTundraCommand(mode=ClimateMode.COOL, temperature=24, turbo=True)
    received = HaierTundraCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.data[6] == 64
    with pytest.raises(ValueError, match="exclusive"):
        HaierTundraCommand(
            mode=ClimateMode.COOL, temperature=24, turbo=True, quiet=True
        )


@pytest.mark.parametrize("temperature", [15.5, 31.5, 24.25])
@pytest.mark.parametrize("cls", [Tcl112Command, PdPioneerClimateCommand])
def test_fractional_temperature_limits(
    cls: type[Tcl112Command] | type[PdPioneerClimateCommand], temperature: float
) -> None:
    """Reject half-degree inputs outside the range and unsupported quarter degrees."""
    with pytest.raises(ValueError, match="temperature"):
        cls(mode=ClimateMode.COOL, temperature=temperature)


@pytest.mark.parametrize(
    "mode,temperature",
    [
        pytest.param(ClimateMode.HEAT, 12, id="below-heat"),
        pytest.param(ClimateMode.HEAT, 28, id="above-heat"),
        pytest.param(ClimateMode.COOL, 16, id="below-cool"),
        pytest.param(ClimateMode.COOL, 33, id="above-cool"),
    ],
)
def test_delonghi_invalid_temperature(mode: ClimateMode, temperature: int) -> None:
    """A mode's temperature field cannot encode the adjacent out-of-range values."""
    with pytest.raises(ValueError, match="temperature"):
        DelonghiCommand(mode=mode, temperature=temperature)


def test_wyt_zero_payload() -> None:
    """The raw transport imposes no climate burst type restriction."""
    sent = PioneerWytCommand(data=bytes(13))
    received = PioneerWytCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.data == bytes(13)

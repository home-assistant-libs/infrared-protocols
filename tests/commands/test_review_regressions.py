"""Independent packet meanings and receiver boundary regressions."""

from collections.abc import Callable

import pytest

from infrared_protocols.commands.airton import AirtonCommand, AirtonDirection
from infrared_protocols.commands.canalsat import CanalSatCommand, CanalSatLDCommand
from infrared_protocols.commands.climate import ClimateFan, ClimateMode
from infrared_protocols.commands.coolix import CoolixCommand
from infrared_protocols.commands.daikin_arc import DaikinArcCommand
from infrared_protocols.commands.delonghi import DelonghiCommand
from infrared_protocols.commands.dyson import (
    DysonAm09Command,
    DysonCommand,
    DysonCoolCommand,
)
from infrared_protocols.commands.gobox import GoboxCommand
from infrared_protocols.commands.gree_models import GreeModel, GreeModelCommand
from infrared_protocols.commands.haier_tundra import HaierTundraCommand
from infrared_protocols.commands.ira211 import Ira211Action, Ira211Command, Ira211Fan
from infrared_protocols.commands.kaseikyo import KaseikyoCommand
from infrared_protocols.commands.lg import Lg28Command, Lg32Command
from infrared_protocols.commands.lg_ac import LgAcCommand, LgAcMode
from infrared_protocols.commands.marantz_extended import MarantzExtendedCommand
from infrared_protocols.commands.midea import MideaCommand
from infrared_protocols.commands.mitsubishi import MitsubishiCommand
from infrared_protocols.commands.noblex import NoblexCommand
from infrared_protocols.commands.panasonic_ac import (
    PanasonicAcCommand,
    PanasonicAcFanSpeed,
    PanasonicAcMode,
    PanasonicAcModel,
    PanasonicAcSwingAxis1,
    PanasonicAcSwingAxis2,
)
from infrared_protocols.commands.pd_pioneer_climate import PdPioneerClimateCommand
from infrared_protocols.commands.pioneer import PioneerCommand
from infrared_protocols.commands.rc5 import RC5Command
from infrared_protocols.commands.rc6 import RC6Command
from infrared_protocols.commands.samsung import Samsung32Command
from infrared_protocols.commands.tcl112 import Tcl112Command
from infrared_protocols.commands.toshiba import ToshibaFan, ToshibaRas25j2kvsgNdCommand
from infrared_protocols.commands.toto import TotoCommand
from infrared_protocols.commands.whirlpool import HisenseArgCommand


@pytest.mark.parametrize(
    "command",
    [
        pytest.param(
            NoblexCommand(mode=ClimateMode.HEAT, temperature=24, power=False),
            id="noblex",
        ),
        pytest.param(
            PdPioneerClimateCommand(mode=ClimateMode.COOL, temperature=24, power=False),
            id="pd-pioneer",
        ),
        pytest.param(
            Tcl112Command(mode=ClimateMode.HEAT, temperature=24, power=False),
            id="tcl112",
        ),
    ],
)
def test_off_mode(
    command: NoblexCommand | PdPioneerClimateCommand | Tcl112Command,
) -> None:
    """Fixed off templates do not identify the retained operating mode."""
    received = type(command).from_raw_timings(command.get_raw_timings())
    assert received is not None
    assert received.state.power is False
    assert received.state.mode is None


@pytest.mark.parametrize("mode", list(ClimateMode))
def test_arc_off_setpoint(mode: ClimateMode) -> None:
    """The off command carries 25 C even when it equals the fan-only sentinel."""
    sent = DaikinArcCommand(mode=mode, temperature=25, power=False)
    received = DaikinArcCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.state.temperature == 25


def test_delonghi_low_heat_off() -> None:
    """Turning off a low heat setpoint does not require a cool-mode temperature."""
    sent = DelonghiCommand(mode=ClimateMode.HEAT, temperature=15, power=False)
    received = DelonghiCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.state.power is False
    assert received.state.temperature is None


@pytest.mark.parametrize("factory", [DysonCoolCommand, DysonAm09Command, DysonCommand])
def test_writable_dyson_button(
    factory: type[DysonCoolCommand] | type[DysonAm09Command] | type[DysonCommand],
) -> None:
    """Changing the public button also changes the transmitted payload."""
    sent = factory(code=1)
    sent.code = 2
    received = factory.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.code == 2
    assert received.button_code == sent.button_code
    assert received.index == sent.index


@pytest.mark.parametrize(
    "sent,decoder",
    [
        pytest.param(
            DysonCoolCommand(code=0x12),
            DysonAm09Command.from_raw_timings,
            id="cool-not-am09",
        ),
        pytest.param(
            DysonAm09Command(code=0x12),
            DysonCoolCommand.from_raw_timings,
            id="am09-not-cool",
        ),
    ],
)
def test_dyson_family_prefix(
    sent: DysonCoolCommand | DysonAm09Command,
    decoder: Callable[[list[int]], DysonCoolCommand | DysonAm09Command | None],
) -> None:
    """A known payload from the other Dyson family is rejected."""
    assert decoder(sent.get_raw_timings()) is None


def test_gobox_family_prefix() -> None:
    """Corrupting only the GoBox prefix must invalidate the command."""
    raw = GoboxCommand(code=0x12).get_raw_timings()
    raw[1] = -1640
    assert GoboxCommand.from_raw_timings(raw) is None


@pytest.mark.parametrize("factory", [Samsung32Command, PioneerCommand])
def test_intermediate_clipped_frame(
    factory: type[Samsung32Command] | type[PioneerCommand],
) -> None:
    """A damaged intermediate frame must not hide a later complete command."""
    raw = factory(address=7, command=2, repeat_count=2).get_raw_timings()
    raw[68:135] = raw[68:79]
    assert factory.from_raw_timings(raw) is None


@pytest.mark.parametrize("preamble", [False, True])
@pytest.mark.parametrize("clipped", [10, 78])
def test_pioneer_clipped_final_repeat(preamble: bool, clipped: int) -> None:
    """A valid command survives truncation of its last repeated frame."""
    sent = PioneerCommand(
        address=7,
        command=2,
        preamble_address=1 if preamble else None,
        preamble_command=3 if preamble else None,
        repeat_count=2,
    )
    received = PioneerCommand.from_raw_timings(sent.get_raw_timings()[:-clipped])
    assert received is not None
    assert (received.address, received.command) == (7, 2)
    assert received.preamble_address == sent.preamble_address


@pytest.mark.parametrize(
    "command",
    [
        pytest.param(RC5Command(address=0, command=0), id="rc5-zero"),
        pytest.param(RC5Command(address=31, command=127, toggle=1), id="rc5-ones"),
        pytest.param(RC6Command(address=0, command=0), id="rc6-zero"),
        pytest.param(RC6Command(address=0, command=0, toggle=1), id="rc6-wide-toggle"),
        pytest.param(
            MarantzExtendedCommand(address=0, command=63, extension=63), id="rc5x"
        ),
    ],
)
@pytest.mark.parametrize("bias", [-150, -100, -50, 50, 100, 150])
@pytest.mark.parametrize("scale", [0.92, 1, 1.08])
def test_manchester_clock_and_bias(
    command: RC5Command | RC6Command | MarantzExtendedCommand, bias: int, scale: float
) -> None:
    """Opposite edge bias must not masquerade as a different Manchester clock."""
    received = type(command).from_raw_timings(
        [round(t * scale) + bias for t in command.get_raw_timings()]
    )
    assert received is not None
    assert received.get_raw_timings() == command.get_raw_timings()


@pytest.mark.parametrize(
    "factory,other",
    [(CanalSatCommand, CanalSatLDCommand), (CanalSatLDCommand, CanalSatCommand)],
)
def test_canalsat_clock_identity(
    factory: type[CanalSatCommand], other: type[CanalSatCommand]
) -> None:
    """Ordinary receiver bias does not confuse the two nominal clocks."""
    sent = factory(device=18, address=35, command=86)
    received = factory.from_raw_timings([t + 40 for t in sent.get_raw_timings()])
    assert received is not None
    assert received.get_raw_timings() == sent.get_raw_timings()
    assert other.from_raw_timings(sent.get_raw_timings()) is None


@pytest.mark.parametrize("length", [291, 292])
def test_mitsubishi_single_copy(length: int) -> None:
    """A default ten-millisecond receiver delivers one complete copy."""
    sent = MitsubishiCommand(mode=ClimateMode.COOL, temperature=23)
    received = MitsubishiCommand.from_raw_timings(sent.get_raw_timings()[:length])
    assert received is not None
    assert received.state.mode == ClimateMode.COOL
    assert received.state.temperature == 23


def test_mitsubishi_different_copies() -> None:
    """Conflicting copies cannot be combined into a single state."""
    first = MitsubishiCommand(mode=ClimateMode.COOL, temperature=23).get_raw_timings()
    second = MitsubishiCommand(mode=ClimateMode.HEAT, temperature=25).get_raw_timings()
    assert MitsubishiCommand.from_raw_timings(first[:292] + second[:291]) is None


@pytest.mark.parametrize("direction", list(AirtonDirection))
def test_airton_features(direction: AirtonDirection) -> None:
    """Auxiliary settings remain accessible after reception."""
    sent = AirtonCommand(
        mode=ClimateMode.COOL,
        temperature=24,
        direction=direction,
        display=False,
        sleep=True,
    )
    received = AirtonCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.direction == direction
    assert received.display is False
    assert received.sleep is True
    assert received.state.swing_v == (direction == AirtonDirection.SWING)


@pytest.mark.parametrize("mode", [ClimateMode.AUTO, ClimateMode.FAN_ONLY])
def test_airton_sleep_unavailable(mode: ClimateMode) -> None:
    """The remote cannot request sleep in automatic or fan-only programs."""
    with pytest.raises(ValueError, match="sleep"):
        AirtonCommand(mode=mode, temperature=24, sleep=True)


def test_gree_horizontal_only_yac() -> None:
    """YAC horizontal motion is independent of the primary vertical enable bit."""
    sent = GreeModelCommand(
        model=GreeModel.YAC, mode=ClimateMode.COOL, temperature=24, swing_h=True
    )
    received = GreeModelCommand.from_raw_timings(
        sent.get_raw_timings(), model=GreeModel.YAC
    )
    assert received is not None
    assert received.state.swing_h is True
    assert received.state.swing_v is False


def test_gree_yaw_followup() -> None:
    """The fixed second YAW1F packet has no independent climate state."""
    sent = GreeModelCommand(
        model=GreeModel.YAW1F, mode=ClimateMode.COOL, temperature=24
    )
    raw = sent.get_raw_timings()
    assert (
        GreeModelCommand.from_raw_timings(
            raw[raw.index(-40000) + 1 :], model=GreeModel.YAW1F
        )
        is None
    )


@pytest.mark.parametrize("quiet,turbo", [(False, False), (True, False), (False, True)])
def test_haier_auxiliary_state(quiet: bool, turbo: bool) -> None:
    """Expose feature settings without requiring callers to inspect payload bits."""
    sent = HaierTundraCommand(
        mode=ClimateMode.COOL, temperature=24, health=True, quiet=quiet, turbo=turbo
    )
    received = HaierTundraCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.health is True
    assert received.quiet == quiet
    assert received.turbo == turbo


def test_ira211_partial_state() -> None:
    """A fan action contains no mode or temperature."""
    sent = Ira211Command(action=Ira211Action.FAN, fan=Ira211Fan.HIGH)
    received = Ira211Command.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.fan == Ira211Fan.HIGH
    assert received.mode is None
    assert received.temperature is None


def test_lg2_roundtrip() -> None:
    """Learned LG2 packets retain their leader and 550-us marks."""
    raw = LgAcCommand(mode=LgAcMode.COOL, temperature=24).get_raw_timings()
    received = Lg28Command.from_raw_timings(raw)
    assert received is not None
    assert received.lg2 is True
    assert received.get_raw_timings() == raw
    assert Lg32Command.from_raw_timings(raw) is None


@pytest.mark.parametrize(
    "mode,temp,fan,packet",
    [
        pytest.param(ClimateMode.COOL, 24, ClimateFan.LOW, "a18847ffff", id="cool-low"),
        pytest.param(
            ClimateMode.COOL, 24, ClimateFan.MEDIUM, "a19047ffff", id="cool-medium"
        ),
        pytest.param(
            ClimateMode.COOL, 24, ClimateFan.AUTO, "a1a047ffff", id="cool-auto"
        ),
        pytest.param(
            ClimateMode.HEAT, 24, ClimateFan.AUTO, "a1a347ffff", id="heat-auto"
        ),
        pytest.param(
            ClimateMode.HEAT, 24, ClimateFan.HIGH, "a19b47ffff", id="heat-high"
        ),
        pytest.param(
            ClimateMode.FAN_ONLY, 24, ClimateFan.AUTO, "a1a45fffff", id="fan-auto"
        ),
    ],
)
def test_midea_control_bytes(
    mode: ClimateMode, temp: int, fan: ClimateFan, packet: str
) -> None:
    """Known control bytes constrain the tables independently of decoding."""
    sent = MideaCommand.climate(mode=mode, temperature=temp, fan=fan)
    assert sent.data == bytes.fromhex(packet)
    state = MideaCommand(data=bytes.fromhex(packet)).state
    assert state is not None
    assert state.mode == mode
    assert state.fan == fan


@pytest.mark.parametrize(
    "mode,temperature,fan,word",
    [
        pytest.param(ClimateMode.COOL, 24, ClimateFan.LOW, 0xB29F40, id="cool24-low"),
        pytest.param(ClimateMode.HEAT, 30, ClimateFan.HIGH, 0xB23FBC, id="heat30-high"),
    ],
)
def test_coolix_control_bytes(
    mode: ClimateMode, temperature: int, fan: ClimateFan, word: int
) -> None:
    """The three-byte word is verified independently of the round trip."""
    assert (
        CoolixCommand.climate(mode=mode, temperature=temperature, fan=fan).first == word
    )


@pytest.mark.parametrize("address,parity", [(0x40, 4), (0x522C, 9)])
def test_kaseikyo_parity(address: int, parity: int) -> None:
    """Address parity is verified on the wire and excluded from application data."""
    sent = KaseikyoCommand(address=address, data=bytes.fromhex("a001ff"))
    raw = sent.get_raw_timings()
    assert raw[35] == (-1263 if parity & 1 else -421)
    received = KaseikyoCommand.from_raw_timings(raw)
    assert received is not None
    assert received.address == address
    assert received.data == sent.data
    assert received.get_raw_timings() == raw


@pytest.mark.parametrize("fan", list(ToshibaFan))
def test_toshiba_native_fan(fan: ToshibaFan) -> None:
    """Every decoded native fan is accepted directly by the state factory."""
    sent = ToshibaRas25j2kvsgNdCommand.climate(
        mode=ClimateMode.COOL, temperature=24, fan=fan
    )
    received = ToshibaRas25j2kvsgNdCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.fan == fan


def test_rc6_nonzero_mode_order() -> None:
    """Mode 6 transmits its bits in the documented LSB-first mode field."""
    raw = RC6Command(mode=6, address=0, command=0, toggle=0).get_raw_timings()
    assert raw[:11] == [2664, -888, 444, -444, 444, -444, 444, -888, 444, -888, 888]


def test_rc6_half_clock_rejected() -> None:
    """Half-unit noise cannot supply a valid clock or cause division by zero."""
    assert RC6Command.from_raw_timings([2664, -888, *([222, -222] * 22)]) is None


@pytest.mark.parametrize(
    "model,axis2",
    [
        pytest.param(PanasonicAcModel.DKE, PanasonicAcSwingAxis2.LEFT, id="dke"),
        pytest.param(PanasonicAcModel.RKR, PanasonicAcSwingAxis2.RIGHT, id="rkr"),
        pytest.param(PanasonicAcModel.LKE, None, id="lke"),
        pytest.param(PanasonicAcModel.NKE, None, id="nke"),
    ],
)
def test_panasonic_native_state(
    model: PanasonicAcModel, axis2: PanasonicAcSwingAxis2 | None
) -> None:
    """The selected model determines which native vane fields are present."""
    sent = PanasonicAcCommand(
        model=model,
        mode=PanasonicAcMode.COOL,
        temperature=24,
        power=False,
        fan=PanasonicAcFanSpeed.MEDIUM_LOW,
        swing_axis1=PanasonicAcSwingAxis1.LOW,
        swing_axis2=axis2,
    )
    received = PanasonicAcCommand.from_raw_timings(sent.get_raw_timings(), model=model)
    assert received is not None
    assert received.state.power is False
    assert received.state.power_toggle is None
    assert received.state.fan == PanasonicAcFanSpeed.MEDIUM_LOW
    assert received.state.swing_axis1 == PanasonicAcSwingAxis1.LOW
    assert received.state.swing_axis2 == axis2
    assert received.state.nanoex is None


def test_panasonic_ckp_toggle() -> None:
    """CKP's power bit carries a toggle and cannot reveal absolute power."""
    sent = PanasonicAcCommand(
        model=PanasonicAcModel.CKP,
        mode=PanasonicAcMode.COOL,
        temperature=24,
        power_toggle=True,
    )
    received = PanasonicAcCommand.from_raw_timings(
        sent.get_raw_timings(), model=PanasonicAcModel.CKP
    )
    assert received is not None
    assert received.state.power is None
    assert received.state.power_toggle is True


def test_panasonic_legacy_nanoex() -> None:
    """Legacy full-state nanoe-X remains readable alongside native vane settings."""
    sent = PanasonicAcCommand(mode=PanasonicAcMode.COOL, temperature=24, nanoex=True)
    received = PanasonicAcCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.state.nanoex is True


def test_hisense_absolute_swing_capture() -> None:
    """The receive fixture sets byte 8 without the transmitter's byte-2 mirror."""
    from infrared_protocols.commands._climate import ClimatePacket

    packet = bytes.fromhex("83060382000080004000008018d90002000008000a")
    command = HisenseArgCommand.__new__(HisenseArgCommand)
    ClimatePacket.__init__(command, data=packet)
    received = HisenseArgCommand.from_raw_timings(command.get_raw_timings())
    assert received is not None
    assert received.state.swing_v is True
    assert received.state.mode == ClimateMode.COOL
    assert received.state.temperature == 24


def test_toto_native_code() -> None:
    """The native little-endian code and legacy nibble view describe one word."""
    sent = TotoCommand(command=0xEC, rc_code_1=0xD, rc_code_2=0xD)
    assert sent.code == 0x37BB
    assert sent.get_raw_timings()[:2] == [6000, -3000]

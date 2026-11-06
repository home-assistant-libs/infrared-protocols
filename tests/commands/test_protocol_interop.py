"""Shared transports and model-specific packet meanings."""

import pytest

from infrared_protocols.codes.coolix.climate import CoolixCode
from infrared_protocols.commands.climate import ClimateFan, ClimateMode, ClimateState
from infrared_protocols.commands.coolix import CoolixCommand
from infrared_protocols.commands.dyson import DysonCommand, DysonCoolCommand
from infrared_protocols.commands.emmeti import EmmetiBlade, EmmetiCommand
from infrared_protocols.commands.gree_models import GreeModel, GreeModelCommand
from infrared_protocols.commands.ira211 import Ira211Action, Ira211Command
from infrared_protocols.commands.kaseikyo import KaseikyoCommand
from infrared_protocols.commands.lg import Lg28Command, Lg32Command
from infrared_protocols.commands.lg_ac import LgAcCommand, LgAcMode
from infrared_protocols.commands.midea import MideaCommand
from infrared_protocols.commands.panasonic_ac import (
    PanasonicAcCommand,
    PanasonicAcFanSpeed,
    PanasonicAcMode,
    PanasonicAcModel,
)
from infrared_protocols.commands.toshiba_48 import ToshibaRas2819Command
from infrared_protocols.commands.toshiba_ac import ToshibaAcPacketCommand
from infrared_protocols.commands.zhlt01 import Zhlt01Command


def test_dyson_shared_payload() -> None:
    """Legacy button tables and the indexed API share one payload decoder."""
    old = DysonCoolCommand(code=0x12)
    received = DysonCommand.from_raw_timings(old.get_raw_timings())
    assert received is not None
    assert (received.button_code, received.index) == (old.button_code, old.index)
    assert (received.code, received.index) == (0x1204, 2)
    assert DysonCommand(code=0x1204, index=2, modulation=38000).modulation == 38000


def test_toshiba_shared_transport() -> None:
    """Model-specific and raw APIs expose the same two 48-bit payloads."""
    sent = ToshibaRas2819Command.climate(mode=ClimateMode.COOL, temperature=24)
    received = ToshibaAcPacketCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.rc_code_1 == int.from_bytes(sent.first)
    assert sent.second is not None
    assert received.rc_code_2 == int.from_bytes(sent.second)


def test_lg_ac_raw_transport() -> None:
    """The raw 28-bit decoder also accepts the LG2 climate header."""
    sent = LgAcCommand(mode=LgAcMode.COOL, temperature=24)
    received = Lg28Command.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.data >> 20 == 0x88
    assert not isinstance(Lg32Command(data=0xABCDEFAB), Lg28Command)


@pytest.mark.parametrize("model", [GreeModel.YAA, GreeModel.YAC1FB9, GreeModel.GENERIC])
def test_gree_latched_vane(model: GreeModel) -> None:
    """A remembered vane nibble alone does not imply active swing."""
    sent = GreeModelCommand(
        model=GreeModel.YAA, mode=ClimateMode.COOL, temperature=24, swing_v=True
    )
    data = bytearray(sent.data)
    data[0] &= ~0x40
    # The swing-enable bit is not included in this checksum.
    sent.data = bytes(data)
    received = GreeModelCommand.from_raw_timings(sent.get_raw_timings(), model=model)
    assert received is not None
    assert received.state.swing_v is False


def test_gree_yan_model_semantics() -> None:
    """YAN's vane nibble carries motion even without the other models' enable bit."""
    sent = GreeModelCommand(
        model=GreeModel.YAN,
        mode=ClimateMode.COOL,
        temperature=24,
        swing_v=True,
        modulation=36000,
    )
    received = GreeModelCommand.from_raw_timings(
        sent.get_raw_timings(), model=GreeModel.YAN
    )
    assert received is not None
    assert received.state.swing_v is True
    assert sent.modulation == 36000


def test_gree_yac_rejects_followup() -> None:
    """The YAW1F secondary packet is not an ordinary YAC state."""
    sent = GreeModelCommand(model=GreeModel.YAC, mode=ClimateMode.COOL, temperature=24)
    sent.data = bytes.fromhex("09082070002020f0")
    assert (
        GreeModelCommand.from_raw_timings(sent.get_raw_timings(), model=GreeModel.YAC)
        is None
    )


def test_gree_yx_vertical_only() -> None:
    """YX1FF has one vane axis; a horizontal-only request cannot be encoded."""
    with pytest.raises(ValueError, match="vertical"):
        GreeModelCommand(
            model=GreeModel.YX1FF, mode=ClimateMode.COOL, temperature=24, swing_h=True
        )
    sent = GreeModelCommand(
        model=GreeModel.YX1FF, mode=ClimateMode.COOL, temperature=24, swing_v=True
    )
    assert sent.state.swing_v is True
    assert sent.state.swing_h is None


@pytest.mark.parametrize("temperature", [8, 10])
def test_panasonic_received_frost_state_section(temperature: int) -> None:
    """A standalone state section exposes 8/10 C frost protection and native fan."""
    sent = PanasonicAcCommand(
        model=PanasonicAcModel.PKE,
        mode=PanasonicAcMode.HEAT,
        temperature=24,
        frost_protection=True,
    )
    assert isinstance(sent.data, list)
    second = bytearray(sent.data[1])
    second[4] = temperature * 2
    second[-1] = (sum(second[:-1]) + 2 + 32) & 255
    raw = KaseikyoCommand(address=0x2002, data=bytes(second)).get_raw_timings()
    received = PanasonicAcCommand.from_raw_timings(raw, model=PanasonicAcModel.PKE)
    assert received is not None
    assert received.state.frost_protection
    assert received.state.temperature == temperature
    assert received.state.fan == PanasonicAcFanSpeed.HIGH
    assert isinstance(received.data, bytes)


def test_panasonic_bad_checksum() -> None:
    """Kaseikyo parity alone cannot validate the application packet."""
    sent = PanasonicAcCommand(mode=PanasonicAcMode.COOL, temperature=24)
    assert isinstance(sent.data, list)
    sent.data[1] = sent.data[1][:-1] + bytes([sent.data[1][-1] ^ 1])
    assert PanasonicAcCommand.from_raw_timings(sent.get_raw_timings()) is None


def test_panasonic_fan_only_has_no_temperature() -> None:
    """The fan-only placeholder is not the user's target temperature."""
    sent = PanasonicAcCommand(mode=PanasonicAcMode.FAN_ONLY, temperature=24)
    received = PanasonicAcCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.state.temperature is None
    assert received.state.mode == PanasonicAcMode.FAN_ONLY


@pytest.mark.parametrize("code", list(CoolixCode))
def test_coolix_action_copies(code: CoolixCode) -> None:
    """Named actions include the protocol's second identical packet."""
    sent = code.to_command()
    assert sent.first == sent.second == code
    assert sent.get_raw_timings().count(-5600) == 1


def test_coolix_unknown_state() -> None:
    """Unknown raw control fields remain raw data without raising on state access."""
    sent = CoolixCommand(first=0xB2FFF0)
    assert sent.state is None


def test_midea_unknown_state() -> None:
    """Checksum-valid but unknown control values do not fabricate a climate state."""
    sent = MideaCommand(data=bytes.fromhex("a1875fffff"))
    received = MideaCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.state is None


def test_midea_sleep_decode() -> None:
    """Sleep is readable after receiving an ordinary control packet."""
    sent = MideaCommand.climate(mode=ClimateMode.COOL, temperature=23, sleep=True)
    received = MideaCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.sleep is True
    assert received.state is not None
    assert received.state.temperature == 23


@pytest.mark.parametrize("blade", list(EmmetiBlade))
@pytest.mark.parametrize("temperature", [16, 22, 30])
def test_emmeti_blades(blade: EmmetiBlade, temperature: int) -> None:
    """Every supported vane position and range is readable from a decoded command."""
    sent = EmmetiCommand(mode=ClimateMode.COOL, temperature=temperature, blade=blade)
    received = EmmetiCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.blade == blade
    assert received.state.temperature == temperature


def test_emmeti_other_off_state() -> None:
    """Power-off is identified by the power bit, beyond the fixed off packet."""
    sent = EmmetiCommand(mode=ClimateMode.COOL, temperature=22)
    sent.data &= ~(1 << 63)
    received = EmmetiCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.state == ClimateState(power=False)


@pytest.mark.parametrize("skew", [-130, 130])
def test_ira211_receiver_bias(skew: int) -> None:
    """A run's error is measured against one unit, allowing receiver edge bias."""
    sent = Ira211Command(action=Ira211Action.POWER, temperature=21.5)
    received = Ira211Command.from_raw_timings(
        [t + skew for t in sent.get_raw_timings()]
    )
    assert received is not None
    assert received.temperature == 21.5
    assert received.action == sent.action


@pytest.mark.parametrize(
    "boost,fan,expected",
    [
        (True, ClimateFan.LOW, ClimateFan.HIGH),
        (False, ClimateFan.QUIET, ClimateFan.QUIET),
    ],
)
def test_zhlt_boost_and_quiet(
    boost: bool, fan: ClimateFan, expected: ClimateFan
) -> None:
    """Boost overrides speed while quiet retains the dedicated low-bit code."""
    sent = Zhlt01Command(mode=ClimateMode.COOL, temperature=24, fan=fan, boost=boost)
    received = Zhlt01Command.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.boost == boost
    assert received.state.fan == expected


@pytest.mark.parametrize("repeat_count", [0, 2])
def test_pioneer_single_frame(repeat_count: int) -> None:
    """Pioneer commands without a preamble decode independently of two-part commands."""
    from infrared_protocols.commands.pioneer import PioneerCommand

    sent = PioneerCommand(address=0xA5, command=0x80, repeat_count=repeat_count)
    received = PioneerCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert (received.address, received.command, received.repeat_count) == (
        0xA5,
        0x80,
        repeat_count,
    )
    assert received.preamble_address is None
    assert received.preamble_command is None

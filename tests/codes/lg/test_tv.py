"""Tests for LG TV command codes."""

from infrared_protocols.codes.lg.tv import LGTVCodeJP
from infrared_protocols.commands.nec import NECCommand
from infrared_protocols.commands.nec1_f16 import NEC1F16Command


def test_lg_tv_jp_normal_command_uses_nec() -> None:
    """Test a normal Japanese LG TV command uses NEC."""
    command = LGTVCodeJP.POWER.to_command()

    assert isinstance(command, NECCommand)
    assert command.address == 0xFB04
    assert command.command == 0x08


def test_lg_tv_jp_app_buttons_use_lg_address() -> None:
    """Test Japanese LG app buttons use the LG TV address."""
    amazon = LGTVCodeJP.AMAZON.to_command()
    netflix = LGTVCodeJP.NETFLIX.to_command()

    assert isinstance(amazon, NECCommand)
    assert amazon.address == 0xFB04
    assert amazon.command == 0x5C

    assert isinstance(netflix, NECCommand)
    assert netflix.address == 0xFB04
    assert netflix.command == 0x56


def test_lg_tv_jp_tuner_selector_uses_nec1_f16() -> None:
    """Test a Japanese LG TV tuner selector uses NEC1-F16."""
    command = LGTVCodeJP.BS.to_command()

    assert isinstance(command, NEC1F16Command)
    assert command.address == 0xFB04
    assert command.function == 0xDB
    assert command.subfunction == 0x00


def test_lg_tv_jp_tuner_number_uses_nec1_f16() -> None:
    """Test a Japanese LG TV tuner number uses NEC1-F16."""
    command = LGTVCodeJP.DTV_NUM_2.to_command()

    assert isinstance(command, NEC1F16Command)
    assert command.address == 0xFB04
    assert command.function == 0xDB
    assert command.subfunction == 0x32


def test_lg_tv_jp_nec1_f16_repeat_count() -> None:
    """Test repeat count is passed to NEC1-F16 commands."""
    command = LGTVCodeJP.BS_NUM_1.to_command(repeat_count=2)

    assert isinstance(command, NEC1F16Command)
    assert command.repeat_count == 2


def test_lg_tv_jp_nec1_f16_command_round_trips() -> None:
    """Test Japanese LG TV NEC1-F16 timings decode correctly."""
    command = LGTVCodeJP.DTV_NUM_2.to_command()

    decoded = NEC1F16Command.from_raw_timings(command.get_raw_timings())

    assert decoded is not None
    assert decoded.address == 0xFB04
    assert decoded.function == 0xDB
    assert decoded.subfunction == 0x32
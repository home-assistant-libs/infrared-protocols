"""Tests for the NAD tuner command codes."""

import pytest

from infrared_protocols.codes.nad.amplifier import (
    NAD_AMPLIFIER_ADDRESS,
    NADAmplifierCode,
)
from infrared_protocols.codes.nad.cd import NADCDCode
from infrared_protocols.codes.nad.tape import NADTapeCode
from infrared_protocols.codes.nad.tuner import NAD_TUNER_ADDRESS, NADTunerCode
from infrared_protocols.commands.nec import NECCommand


def test_nad_tuner_codes_are_unique() -> None:
    """Every code must be distinct, since duplicates become silent aliases."""
    members = NADTunerCode.__members__
    assert len(members) == len(set(members.values()))


@pytest.mark.parametrize(
    "other",
    [
        pytest.param(NADAmplifierCode, id="amplifier"),
        pytest.param(NADCDCode, id="cd"),
        pytest.param(NADTapeCode, id="tape"),
    ],
)
def test_nad_tuner_codes_do_not_overlap(
    other: type[NADAmplifierCode | NADCDCode | NADTapeCode],
) -> None:
    """All NAD components share one address, so their codes must not collide."""
    assert NAD_TUNER_ADDRESS == NAD_AMPLIFIER_ADDRESS
    assert not {code.value for code in NADTunerCode} & {code.value for code in other}


@pytest.mark.parametrize(
    ("code", "command"),
    [
        pytest.param(NADTunerCode.FM, 0x81, id="fm"),
        pytest.param(NADTunerCode.PRESET_UP, 0xD2, id="preset_up"),
        pytest.param(NADTunerCode.NUM_0, 0xC7, id="num_0"),
        pytest.param(NADTunerCode.NUM_1, 0x8A, id="num_1"),
    ],
)
def test_nad_tuner_code_to_command(code: NADTunerCode, command: int) -> None:
    """Each code builds an extended NEC command on the NAD address."""
    built = code.to_command()
    assert isinstance(built, NECCommand)
    assert built.address == NAD_TUNER_ADDRESS
    assert built.command == command

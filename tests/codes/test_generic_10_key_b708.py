"""Tests for the generic 10-key LED candle remote on NEC address 0xB708."""

import pytest

from infrared_protocols.codes.generic.led import Generic10KeyB708Code
from infrared_protocols.commands.nec import NECCommand
from infrared_protocols.commands.pronto import ProntoCommand


def test_generic_10_key_b708_codes_are_unique() -> None:
    """Every code must be distinct, since duplicates become silent aliases."""
    members = Generic10KeyB708Code.__members__
    assert len(members) == len(set(members.values()))


# Captured from the original remote of a Flinq LED candle.
@pytest.mark.parametrize(
    ("code", "pronto_hex"),
    [
        pytest.param(
            Generic10KeyB708Code.ON,
            "0000 006D 0022 0000 0159 00AD 0016 0016 0016 0016 0016 0016 0016 0041 "
            "0016 0016 0016 0016 0016 0016 0016 0016 0016 0041 0016 0041 0016 0041 "
            "0016 0016 0016 0041 0016 0041 0016 0016 0016 0041 0016 0016 0016 0016 "
            "0016 0016 0016 0016 0016 0016 0016 0016 0016 0016 0016 0016 0016 0041 "
            "0016 0041 0016 0041 0016 0041 0016 0041 0016 0041 0016 0041 0016 0041 "
            "0016 0181",
            id="on",
        ),
        pytest.param(
            Generic10KeyB708Code.OFF,
            "0000 006D 0022 0000 0158 00AC 0016 0016 0016 0016 0016 0016 0016 0041 "
            "0016 0016 0016 0016 0016 0016 0016 0016 0016 0041 0016 0041 0016 0041 "
            "0016 0016 0016 0041 0016 0041 0016 0016 0016 0041 0016 0016 0016 0041 "
            "0016 0016 0016 0016 0016 0016 0016 0016 0016 0016 0016 0016 0016 0041 "
            "0016 0016 0016 0041 0016 0041 0016 0041 0016 0041 0016 0041 0016 0041 "
            "0016 0181",
            id="off",
        ),
    ],
)
def test_generic_10_key_b708_matches_capture(
    code: Generic10KeyB708Code, pronto_hex: str
) -> None:
    """The captured frame decodes to the same NEC address and command."""
    timings = ProntoCommand.from_pronto_hex(pronto_hex).get_raw_timings()
    decoded = NECCommand.from_raw_timings(timings)
    assert decoded is not None
    built = code.to_command()
    assert isinstance(built, NECCommand)
    assert decoded.address == built.address == 0xB708
    assert decoded.command == built.command == code.value


def test_generic_10_key_b708_round_trips_through_the_decoder() -> None:
    """Every code must decode back to itself from its own timings."""
    for code in Generic10KeyB708Code:
        decoded = NECCommand.from_raw_timings(code.to_command().get_raw_timings())
        assert decoded is not None
        assert decoded.address == 0xB708
        assert decoded.command == code.value

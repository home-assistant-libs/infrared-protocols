"""Tests for the hob2hood named command codes."""

import pytest

from infrared_protocols.codes.hob2hood.hood import Hob2HoodCode
from infrared_protocols.commands.hob2hood import Hob2HoodCommand


def test_codes_are_unique() -> None:
    """Duplicate values must not silently turn named buttons into aliases."""
    members = Hob2HoodCode.__members__
    assert len(members) == len(set(members.values()))


@pytest.mark.parametrize("code", list(Hob2HoodCode))
def test_hob2hood_codes(code: Hob2HoodCode) -> None:
    """Every named extractor command decodes back to its command byte."""
    command = code.to_command()
    decoded = Hob2HoodCommand.from_raw_timings(command.get_raw_timings())
    assert decoded is not None
    assert decoded.command == code.value

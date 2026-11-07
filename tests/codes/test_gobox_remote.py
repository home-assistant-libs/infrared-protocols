"""Tests for the gobox named command codes."""

import pytest

from infrared_protocols.codes.gobox.remote import GoboxCode
from infrared_protocols.commands.gobox import GoboxCommand


def test_codes_are_unique() -> None:
    """Duplicate values must not silently turn named buttons into aliases."""
    members = GoboxCode.__members__
    assert len(members) == len(set(members.values()))


@pytest.mark.parametrize("code", list(GoboxCode))
def test_gobox_codes(code: GoboxCode) -> None:
    """Every named remote button decodes back to its code."""
    decoded = GoboxCommand.from_raw_timings(code.to_command().get_raw_timings())
    assert decoded is not None
    assert decoded.code == code.value

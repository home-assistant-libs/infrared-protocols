"""Tests for gobox protocol behavior."""

from infrared_protocols.commands.gobox import GoboxCommand


def test_gobox_family_prefix() -> None:
    """Corrupting only the GoBox prefix must invalidate the command."""
    raw = GoboxCommand(code=0x12).get_raw_timings()
    raw[1] = -1640
    assert GoboxCommand.from_raw_timings(raw) is None

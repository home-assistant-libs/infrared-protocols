"""Tests for magiquest protocol behavior."""

from infrared_protocols.commands.magiquest import (
    MagiQuestLegacyCommand,
)


def test_magiquest_legacy_fields() -> None:
    """The deployed legacy payload has its own complete receiver."""
    sent = MagiQuestLegacyCommand(wand_id=0x12345678, magnitude=0xABCD)
    received = MagiQuestLegacyCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert (received.wand_id, received.magnitude) == (0x12345678, 0xABCD)

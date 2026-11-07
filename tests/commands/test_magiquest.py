"""Tests for magiquest protocol behavior."""

import pytest

from infrared_protocols.commands.magiquest import (
    MagiQuestCommand,
    MagiQuestLegacyCommand,
)


def test_magiquest_legacy_fields() -> None:
    """The deployed legacy payload has its own complete receiver."""
    sent = MagiQuestLegacyCommand(wand_id=0x12345678, magnitude=0xABCD)
    received = MagiQuestLegacyCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert (received.wand_id, received.magnitude) == (0x12345678, 0xABCD)


@pytest.mark.parametrize(
    "wand_id,magnitude", [(0, 0), (0x12345678, 0x123), (0x7FFFFFFF, 511)]
)
@pytest.mark.parametrize("trim", [0, 1])
def test_magiquest_wand(wand_id: int, magnitude: int, trim: int) -> None:
    """Decode complete wand messages with an optional final space."""
    command = MagiQuestCommand(wand_id=wand_id, magnitude=magnitude)
    raw = command.get_raw_timings()
    decoded = MagiQuestCommand.from_raw_timings(raw[: len(raw) - trim])
    assert decoded is not None
    assert (decoded.wand_id, decoded.magnitude) == (wand_id, magnitude)


def test_magiquest_checksum() -> None:
    """A changed checksum symbol must be rejected."""
    raw = MagiQuestCommand(wand_id=0x12345678, magnitude=0x123).get_raw_timings()
    raw[-2:] = [576, -576]
    assert MagiQuestCommand.from_raw_timings(raw) is None

"""Tests for beo4 protocol behavior."""

from infrared_protocols.commands.beo4 import Beo4Command


def test_beolink_repeated_capture() -> None:
    """The link bit is data and multiple identical frames are accepted."""
    sent = Beo4Command(source=0x12, command=0xA5, link=True)
    raw = sent.get_raw_timings()
    received = Beo4Command.from_raw_timings(raw + [-30000] + raw)
    assert received is not None
    assert received.link
    assert (received.source, received.command) == (
        0x12,
        0xA5,
    )

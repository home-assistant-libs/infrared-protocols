"""Tests for toto protocol behavior."""

import pytest

from infrared_protocols.commands.toto import TotoCommand


def test_toto_native_code() -> None:
    """The native little-endian code and legacy nibble view describe one word."""
    sent = TotoCommand(command=0xEC, rc_code_1=0xD, rc_code_2=0xD)
    assert sent.code == 0x37BB
    assert sent.get_raw_timings()[:2] == [6000, -3000]


def test_toto_three_transmissions() -> None:
    """A Toto button always transmits three copies 36 ms apart."""
    sent = TotoCommand(command=0xED, rc_code_1=3, rc_code_2=9)
    raw = sent.get_raw_timings()
    assert raw.count(-36000) == 2
    received = TotoCommand.from_raw_timings(raw)
    assert received is not None
    assert (received.command, received.rc_code_1, received.rc_code_2) == (0xED, 3, 9)


def test_header_alone_rejected() -> None:
    """A Toto leader without fields cannot become a command."""
    assert TotoCommand.from_raw_timings([6000, -3000]) is None


@pytest.mark.parametrize(
    "trailing",
    [pytest.param([], id="single"), pytest.param([-20000], id="trailing-idle")],
)
def test_single_frame(trailing: list[int]) -> None:
    """A receiver may split each copy at the inter-frame gap."""
    sent = TotoCommand(command=0xED, rc_code_1=3, rc_code_2=9)
    raw = sent.get_raw_timings()
    received = TotoCommand.from_raw_timings(raw[: raw.index(-36000)] + trailing)
    assert received is not None
    assert (received.command, received.rc_code_1, received.rc_code_2) == (0xED, 3, 9)


def test_mismatched_last_copy() -> None:
    """Individually valid copies must carry the same command."""
    raw = TotoCommand(command=0xED, rc_code_1=3, rc_code_2=9).get_raw_timings()
    different = TotoCommand(command=0xEC, rc_code_1=3, rc_code_2=9).get_raw_timings()
    frame_length = raw.index(-36000)
    raw[-frame_length:] = different[:frame_length]
    assert TotoCommand.from_raw_timings(raw) is None


def test_bad_checksum() -> None:
    """A flipped XOR checksum bit invalidates a standalone frame."""
    raw = TotoCommand(command=0xED, rc_code_1=3, rc_code_2=9).get_raw_timings()
    frame = raw[: raw.index(-36000)]
    assert frame[-2] == -520
    frame[-2] = -1667
    assert TotoCommand.from_raw_timings(frame) is None

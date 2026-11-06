"""Tests for toto protocol behavior."""

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

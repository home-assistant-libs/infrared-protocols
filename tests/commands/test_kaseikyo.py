"""Tests for the Kaseikyo format IR command."""

import json
from itertools import product
from pathlib import Path

import pytest

from infrared_protocols.commands.kaseikyo import KaseikyoCommand


def test_kaseikyo_command_get_raw_timings() -> None:
    """Test Kaseikyo command raw timings."""
    # Kaseikyo format frame for address=0x1234, data=[0x5, 0x67], no error correction
    # T = 421μs (base unit for 38kHz with burst pulse of 16)
    expected_raw_timings = [
        # Leader
        3368,
        -1684,
        # Address low: 0x34 (LSB first: 0,0,1,0,1,1,0,0)
        421,
        -421,
        421,
        -421,
        421,
        -1263,
        421,
        -421,
        421,
        -1263,
        421,
        -1263,
        421,
        -421,
        421,
        -421,
        # Address high: 0x12 (LSB first: 0,1,0,0,1,0,0,0)
        421,
        -421,
        421,
        -1263,
        421,
        -421,
        421,
        -421,
        421,
        -1263,
        421,
        -421,
        421,
        -421,
        421,
        -421,
        # Parity (Address XORed per 4 bits): 0x1^0x2^0x3^0x4 = 0x4 (LSB first: 0,0,1,0)
        421,
        -421,
        421,
        -421,
        421,
        -1263,
        421,
        -421,
        # Data 0: 0x5 (LSB first: 1,0,1,0)
        421,
        -1263,
        421,
        -421,
        421,
        -1263,
        421,
        -421,
        # Data 1: 0x67 (LSB first: 1,1,1,0,0,1,1,0)
        421,
        -1263,
        421,
        -1263,
        421,
        -1263,
        421,
        -421,
        421,
        -421,
        421,
        -1263,
        421,
        -1263,
        421,
        -421,
        # End pulse
        421,
    ]
    command = KaseikyoCommand(address=0x1234, data=bytes([0x50, 0x67]))
    timings = command.get_raw_timings()
    assert timings == expected_raw_timings
    assert command.modulation == 38000

    # Frame duration: 3368 + 1684 + 32*421 + 13*1263 + 19*421 + 421 = 43363
    #   Gap = 130000 - 43363 = 86637
    # Repeat code duration: 3368 + 3368 + 421 = 7157
    #   Gap = 130000 - 7157 = 122843
    command_with_repeats = KaseikyoCommand(
        address=command.address,
        data=command.data,
        repeat_count=2,
    )
    timings_with_repeats = command_with_repeats.get_raw_timings()
    expected_repeat_code_raw_timings = [
        # Leader
        3368,
        -3368,
        # End pulse
        421,
    ]
    assert timings_with_repeats == [
        *expected_raw_timings,
        -86637,
        *expected_repeat_code_raw_timings,
        -122843,
        *expected_repeat_code_raw_timings,
    ]


_CAPTURES = json.loads(
    (Path(__file__).parents[1] / "fixtures/receiver_captures.json").read_text()
)["captures"]

_DECODE_CASES = [
    pytest.param(
        KaseikyoCommand(address=a, data=d, repeat_count=r), id=f"{a:#06x}-{d!r}-r{r}"
    )
    for a, d, r in product(
        (0, 8194, 65535),
        (bytes([0]), bytes([160, 1, 255]), [bytes([160, 1]), bytes([176, 255])]),
        (0, 2),
    )
]


@pytest.mark.parametrize("address,parity", [(0x40, 4), (0x522C, 9)])
def test_kaseikyo_parity(address: int, parity: int) -> None:
    """Address parity is verified on the wire and excluded from application data."""
    sent = KaseikyoCommand(address=address, data=bytes.fromhex("a001ff"))
    raw = sent.get_raw_timings()
    assert raw[35] == (-1263 if parity & 1 else -421)
    received = KaseikyoCommand.from_raw_timings(raw)
    assert received is not None
    assert received.address == address
    assert received.data == sent.data
    assert received.get_raw_timings() == raw


def test_kaseikyo_full_frame_repeat() -> None:
    """Identical frames on the 130-ms period retain their held-key timing."""
    command = KaseikyoCommand(
        address=0x2002, data=b"\xa0\x01\xff", repeat_count=2, full_frame_repeat=True
    )
    raw = command.get_raw_timings()
    received = KaseikyoCommand.from_raw_timings(raw + [-5000])
    assert received is not None
    assert received.data == b"\xa0\x01\xff"
    assert received.repeat_count == 2
    assert received.full_frame_repeat
    assert received.get_raw_timings() == raw


@pytest.mark.parametrize(
    "sections",
    [
        pytest.param([b"\xa0\x01", b"\xb0\x02"], id="different-sections"),
        pytest.param([b"\xa0\x01", b"\xa0\x01"], id="identical-sections"),
    ],
)
def test_kaseikyo_multi_section_full_repeat_rejected(sections: list[bytes]) -> None:
    """Do not offer group repeats whose boundaries cannot be decoded reliably."""
    with pytest.raises(ValueError, match="single payload section"):
        KaseikyoCommand(
            address=0x2002, data=sections, repeat_count=2, full_frame_repeat=True
        )


def test_kaseikyo_section_gap_preserved() -> None:
    """An application message's section gap is not normalized to ten milliseconds."""
    raw = KaseikyoCommand(
        address=0x2002, data=[b"\xa0\x01", b"\xb0\x02"]
    ).get_raw_timings()
    raw[raw.index(-10000)] = -18000
    received = KaseikyoCommand.from_raw_timings(raw)
    assert received is not None
    assert received.repeat_count == 0
    assert received.get_raw_timings() == raw


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param(bytes.fromhex("f0ffffffff"), id="shorter-than-repeat-period"),
        pytest.param(bytes.fromhex("f0ffffffffffff"), id="near-repeat-period"),
    ],
)
@pytest.mark.parametrize("scale", [0.85, 1.0, 1.15])
def test_kaseikyo_identical_sections(payload: bytes, scale: float) -> None:
    """Identical application sections retain their ten-millisecond gap."""
    command = KaseikyoCommand(address=0xFFFF, data=[payload, payload])
    raw = [round(t * scale) for t in command.get_raw_timings()]
    received = KaseikyoCommand.from_raw_timings(raw)
    assert received is not None
    assert received.data == [payload, payload]
    assert received.repeat_count == 0
    assert not received.full_frame_repeat
    assert [t for t in received.get_raw_timings() if t < -5000] == [
        -round(10000 * scale)
    ]


@pytest.mark.parametrize("scale", [0.85, 1.15])
@pytest.mark.parametrize("bias", [-100, 0, 100])
def test_kaseikyo_repeat_clock(scale: float, bias: int) -> None:
    """The held-key period follows the observed clock and retains received gaps."""
    command = KaseikyoCommand(
        address=0x2002, data=b"\xa0\x01\xff", repeat_count=2, full_frame_repeat=True
    )
    raw = [round(t * scale) + bias for t in command.get_raw_timings()]
    received = KaseikyoCommand.from_raw_timings(raw)
    assert received is not None
    assert received.data == command.data
    assert received.repeat_count == 2
    assert received.full_frame_repeat
    assert [t for t in received.get_raw_timings() if t < -5000] == [
        t for t in raw if t < -5000
    ]


def test_recorded_kaseikyo() -> None:
    """The Panasonic capture preserves its manufacturer and application bytes."""
    capture = next(c for c in _CAPTURES if c["protocol"] == "kaseikyo")
    result = KaseikyoCommand.from_raw_timings(capture["timings"])
    assert result is not None
    assert result.address == 0x2002
    assert result.data == bytes.fromhex("10ff7699")


@pytest.mark.parametrize("command", _DECODE_CASES)
def test_decoder_round_trip_fields(command: KaseikyoCommand) -> None:
    """Decode edge-valued fields and preserve their protocol meaning."""
    raw = command.get_raw_timings()
    result = KaseikyoCommand.from_raw_timings(raw)
    assert result is not None
    assert result.get_raw_timings() == raw
    assert result.address == command.address
    assert result.data == command.data
    assert result.repeat_count == command.repeat_count


@pytest.mark.parametrize("command", _DECODE_CASES)
@pytest.mark.parametrize("prefix", [0, 1, 5])
def test_decoder_truncated(command: KaseikyoCommand, prefix: int) -> None:
    """A partial leader or payload cannot be a complete command."""
    assert KaseikyoCommand.from_raw_timings(command.get_raw_timings()[:prefix]) is None

"""Tests for pioneer wyt protocol behavior."""

import pytest

from infrared_protocols.commands.pioneer_wyt import PioneerWytCommand


@pytest.mark.parametrize(
    "data,checksum",
    [
        pytest.param(bytes(13), 0, id="zero"),
        *[
            pytest.param(
                bytes([0x23, 0xCB, 0x26, packet_type, 0, 0x24, 3, 7, 5, 0x80, 0, 0, 0]),
                (0xC7 + packet_type + (15 if packet_type == 2 else 0)) & 255,
                id=f"type-{packet_type}",
            )
            for packet_type in (0, 1, 2, 7, 255)
        ],
    ],
)
def test_wyt_application_types(data: bytes, checksum: int) -> None:
    """Raw WYT accepts all application types and adds fifteen only for type two."""
    sent = PioneerWytCommand(data=data)
    assert sent.checksum(sent.data) == checksum
    received = PioneerWytCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.data == data

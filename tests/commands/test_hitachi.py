"""Tests for hitachi protocol behavior."""

import pytest

from infrared_protocols.commands.climate import ClimateFan, ClimateMode
from infrared_protocols.commands.hitachi import (
    HitachiAc344Command,
    HitachiAc424Command,
    HitachiButton,
)


@pytest.mark.parametrize(
    "cls,mode_code",
    [
        pytest.param(HitachiAc344Command, 7, id="344"),
        pytest.param(HitachiAc424Command, 14, id="424"),
    ],
)
def test_hitachi_receive_auto_maximum(
    cls: type[HitachiAc344Command], mode_code: int
) -> None:
    """Receive-only mode and speed codes remain explicit rather than rejected."""
    sent = cls(mode=ClimateMode.COOL, temperature=24)
    data = bytearray(sent.data)
    data[25] = 0x60 | mode_code
    data[26] = data[25] ^ 255
    sent.data = bytes(data)
    received = cls.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.state.mode == ClimateMode.AUTO
    assert received.state.fan == ClimateFan.MAXIMUM


def test_hitachi_mildew_and_quiet() -> None:
    """Mildew shutdown and quiet operation use distinct auxiliary bytes."""
    off = HitachiAc344Command(
        mode=ClimateMode.COOL,
        temperature=24,
        power=False,
        mildew_proof=True,
        button=HitachiButton.MILDEW_PROOF,
    )
    quiet = HitachiAc344Command(
        mode=ClimateMode.COOL, temperature=24, fan=ClimateFan.QUIET
    )
    assert off.data[9] == 0xA5
    assert quiet.data[9] == 0x98
    received = HitachiAc344Command.from_raw_timings(off.get_raw_timings())
    assert received is not None
    assert received.button == HitachiButton.MILDEW_PROOF
    assert received.state.power is False

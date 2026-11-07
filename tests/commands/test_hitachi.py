"""Tests for hitachi protocol behavior."""

import pytest

from infrared_protocols.commands.hitachi import (
    HitachiAc344Command,
    HitachiAc424Command,
    HitachiButton,
    HitachiFanSpeed,
    HitachiMode,
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
    sent = cls(mode=HitachiMode.COOL, temperature=24)
    data = bytearray(sent.data)
    data[25] = 0x60 | mode_code
    data[26] = data[25] ^ 255
    sent.data = bytes(data)
    received = cls.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.state.mode == HitachiMode.AUTO
    assert received.state.fan == HitachiFanSpeed.MAXIMUM


def test_hitachi_mildew_and_quiet() -> None:
    """Mildew shutdown and quiet operation use distinct auxiliary bytes."""
    off = HitachiAc344Command(
        mode=HitachiMode.COOL,
        temperature=24,
        power=False,
        mildew_proof=True,
        button=HitachiButton.MILDEW_PROOF,
    )
    quiet = HitachiAc344Command(
        mode=HitachiMode.COOL, temperature=24, fan=HitachiFanSpeed.QUIET
    )
    assert off.data[9] == 0xA5
    assert quiet.data[9] == 0x98
    received = HitachiAc344Command.from_raw_timings(off.get_raw_timings())
    assert received is not None
    assert received.mildew_proof
    assert received.button == HitachiButton.MILDEW_PROOF
    assert received.state.power is False


def test_unknown_button_rejected() -> None:
    """An unsupported button cannot be encoded."""
    with pytest.raises(ValueError):
        HitachiAc344Command(mode=HitachiMode.COOL, temperature=24, button=255)  # type: ignore[arg-type]


def test_unknown_received_button() -> None:
    """A valid checksum cannot legitimize an unsupported action identifier."""
    sent = HitachiAc344Command(mode=HitachiMode.COOL, temperature=24)
    sent.data = bytes.fromhex(
        "01100040bfff00cc33926d22dd609f00ff00ff00ff00ff00ff53acf10e01fe01fe807f03fc00ff00ff00ff"
    )
    assert HitachiAc344Command.from_raw_timings(sent.get_raw_timings()) is None


@pytest.mark.parametrize(
    "factory",
    [
        pytest.param(HitachiAc344Command, id="344"),
        pytest.param(HitachiAc424Command, id="424"),
    ],
)
@pytest.mark.parametrize("position", range(6))
def test_horizontal_position_readback(
    factory: type[HitachiAc344Command], position: int
) -> None:
    """Every fixed horizontal vane position survives a temperature change."""
    sent = factory(mode=HitachiMode.COOL, temperature=24, horizontal_position=position)
    received = factory.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.horizontal_position == position
    rebuilt = factory(
        mode=HitachiMode.COOL,
        temperature=25,
        horizontal_position=received.horizontal_position,
    )
    assert rebuilt.data[35:37] == received.data[35:37]
    assert rebuilt.state.temperature == 25

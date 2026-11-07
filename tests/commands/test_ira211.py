"""Tests for ira211 protocol behavior."""

import pytest

from infrared_protocols.commands._timing import bits, runs
from infrared_protocols.commands.ira211 import (
    Ira211Action,
    Ira211Command,
    Ira211FanSpeed,
    Ira211Mode,
)


def test_ira211_partial_state() -> None:
    """A fan action contains no mode or temperature."""
    sent = Ira211Command(action=Ira211Action.FAN, fan=Ira211FanSpeed.HIGH)
    received = Ira211Command.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.fan == Ira211FanSpeed.HIGH
    assert received.mode is None
    assert received.temperature is None


@pytest.mark.parametrize("skew", [-130, 130])
def test_ira211_receiver_bias(skew: int) -> None:
    """A run's error is measured against one unit, allowing receiver edge bias."""
    sent = Ira211Command(action=Ira211Action.POWER, temperature=21.5)
    received = Ira211Command.from_raw_timings(
        [t + skew for t in sent.get_raw_timings()]
    )
    assert received is not None
    assert received.temperature == 21.5
    assert received.action == sent.action


@pytest.mark.parametrize("action", list(Ira211Action))
@pytest.mark.parametrize("temperature", [5, 20.5, 35])
def test_ira211_actions(action: Ira211Action, temperature: float) -> None:
    """Every action carries exactly its own fields."""
    command = Ira211Command(
        action=action,
        temperature=temperature,
        mode=Ira211Mode.TIMER,
        fan=Ira211FanSpeed.HIGH,
    )
    decoded = Ira211Command.from_raw_timings(command.get_raw_timings())
    assert decoded is not None
    assert decoded.get_raw_timings() == command.get_raw_timings()


def _framed_packet(wire: bytes) -> list[int]:
    """Wrap independently supplied bytes in IRA211 start/stop bits."""
    levels = [bit for byte in wire for bit in [1, *bits(byte, 8), 0]]
    return [7600, -800, 800, -7600, *runs(levels, 800), 800, -7600]


@pytest.mark.parametrize(
    "wire",
    [
        pytest.param(bytes.fromhex("661f575faa3f98"), id="checksum"),
        pytest.param(bytes.fromhex("651f575faa3f9b"), id="device-id"),
        pytest.param(bytes.fromhex("66df575f92"), id="field-count"),
        pytest.param(bytes.fromhex("663f575faa3fb9"), id="unknown-action"),
        pytest.param(bytes.fromhex("661f575f7f3f42"), id="unknown-mode"),
        pytest.param(bytes.fromhex("661f575faa7fd9"), id="unknown-fan"),
        pytest.param(bytes.fromhex("661f57bfaa3f39"), id="invalid-tenths"),
    ],
)
def test_invalid_wire_fields(wire: bytes) -> None:
    """Validate checksum, identity, action length and state values independently."""
    assert Ira211Command.from_raw_timings(_framed_packet(wire)) is None


@pytest.mark.parametrize(
    "index", [pytest.param(10, id="start-bit"), pytest.param(19, id="stop-bit")]
)
def test_invalid_byte_framing(index: int) -> None:
    """A correct payload and checksum cannot repair a broken byte boundary."""
    wire = bytes.fromhex("661f575faa3f99")
    levels = [bit for byte in wire for bit in [1, *bits(byte, 8), 0]]
    levels[index] ^= 1
    raw = [7600, -800, 800, -7600, *runs(levels, 800), 800, -7600]
    assert Ira211Command.from_raw_timings(raw) is None


def test_power_then_sync_in_one_capture() -> None:
    """A 7.6-ms gap ends the first action even when the receiver captures both."""
    power = Ira211Command(action=Ira211Action.POWER, temperature=21.5)
    sync = Ira211Command(action=Ira211Action.SYNC, temperature=21.5)
    received = Ira211Command.from_raw_timings(
        power.get_raw_timings() + sync.get_raw_timings()
    )
    assert received is not None
    assert received.action is Ira211Action.POWER
    assert received.temperature == 21.5
    assert received.get_raw_timings() == power.get_raw_timings()

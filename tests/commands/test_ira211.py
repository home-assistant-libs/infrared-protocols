"""Tests for ira211 protocol behavior."""

import pytest

from infrared_protocols.commands.ira211 import Ira211Action, Ira211Command, Ira211Fan


def test_ira211_partial_state() -> None:
    """A fan action contains no mode or temperature."""
    sent = Ira211Command(action=Ira211Action.FAN, fan=Ira211Fan.HIGH)
    received = Ira211Command.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.fan == Ira211Fan.HIGH
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

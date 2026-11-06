"""Tests for hob2hood protocol behavior."""

import pytest

from infrared_protocols.codes.hob2hood.hood import Hob2HoodCode
from infrared_protocols.commands.hob2hood import Hob2HoodCommand


@pytest.mark.parametrize("code", list(Hob2HoodCode))
def test_hob_receiver_skew_and_idle(code: Hob2HoodCode) -> None:
    """Measured receiver bias fits the documented absolute tolerance."""
    raw = code.to_command().get_raw_timings()
    biased = [t - 240 for t in raw]
    received = Hob2HoodCommand.from_raw_timings(biased + [-20000])
    assert received is not None
    assert received.command == code


@pytest.mark.parametrize(
    "code",
    [code for code in Hob2HoodCode if code.to_command().get_raw_timings()[-1] < 0],
)
@pytest.mark.parametrize("tail", [[], [-20000]], ids=["omitted", "merged-idle"])
def test_hob_dropped_final_space(code: Hob2HoodCode, tail: list[int]) -> None:
    """Some receivers stop before reporting the final space."""
    received = Hob2HoodCommand.from_raw_timings(
        [t - 240 for t in code.to_command().get_raw_timings()[:-1]] + tail
    )
    assert received is not None
    assert received.command == code


def test_hob_unknown_command() -> None:
    """Only the seven supported hood actions can be encoded."""
    with pytest.raises(ValueError):
        Hob2HoodCommand(command=0)

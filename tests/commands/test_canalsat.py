"""Tests for canalsat protocol behavior."""

import pytest

from infrared_protocols.commands.canalsat import CanalSatCommand, CanalSatLDCommand


@pytest.mark.parametrize(
    "factory,other",
    [(CanalSatCommand, CanalSatLDCommand), (CanalSatLDCommand, CanalSatCommand)],
)
def test_canalsat_clock_identity(
    factory: type[CanalSatCommand], other: type[CanalSatCommand]
) -> None:
    """Ordinary receiver bias does not confuse the two nominal clocks."""
    sent = factory(device=18, address=35, command=86)
    received = factory.from_raw_timings([t + 40 for t in sent.get_raw_timings()])
    assert received is not None
    assert received.get_raw_timings() == sent.get_raw_timings()
    assert other.from_raw_timings(sent.get_raw_timings()) is None

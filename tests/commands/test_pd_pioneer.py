"""Tests for pd pioneer protocol behavior."""

import pytest

from infrared_protocols.commands._timing import byte_bits
from infrared_protocols.commands.pd_pioneer import PdPioneerCommand
from infrared_protocols.commands.pd_pioneer_climate import (
    PdPioneerClimateCommand,
    PdPioneerClimateMode,
)


@pytest.mark.parametrize(
    "temperature,wire_temperature",
    [
        pytest.param(16, 0x80, id="minimum"),
        pytest.param(16.5, 0x84, id="low-half"),
        pytest.param(24.5, 0x84, id="normal-half"),
        pytest.param(30.5, 0x84, id="high-half"),
        pytest.param(31, 0x80, id="maximum"),
    ],
)
def test_pd_half_degree_economy(temperature: float, wire_temperature: int) -> None:
    """Both state bursts retain fractional targets and the economy flag."""
    sent = PdPioneerClimateCommand(
        mode=PdPioneerClimateMode.COOL, temperature=temperature, economy=True
    )
    received = PdPioneerClimateCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert received.state.temperature == temperature
    assert received.economy
    assert sent.data[19] == 0x25
    assert sent.data[26] == wire_temperature


@pytest.mark.parametrize(
    "burst,checksum",
    [pytest.param(1, 0x15, id="even"), pytest.param(2, 0x25, id="odd")],
)
def test_pd_burst_types(burst: int, checksum: int) -> None:
    """Both burst types use their specified checksum offset."""
    sent = PdPioneerCommand(data=bytes([0x23, 0xCB, 0x26, burst] + [0] * 9))
    assert sent.checksum(sent.data) == checksum
    result = PdPioneerCommand.from_raw_timings(sent.get_raw_timings())
    assert result is not None
    assert result.data == sent.data


def test_pd_type_zero_rejected() -> None:
    """Unknown burst types remain invalid even with a matching byte sum."""
    payload = bytes([0x23, 0xCB, 0x26] + [0] * 10)
    with pytest.raises(ValueError, match="burst type"):
        PdPioneerCommand(data=payload)
    raw = [
        3120,
        -1560,
        *PdPioneerCommand.TIMING.encode(byte_bits(payload + b"\x14")),
        520,
        -10010,
    ]
    assert PdPioneerCommand.from_raw_timings(raw) is None


@pytest.mark.parametrize(
    "temperature",
    [
        pytest.param(15.5, id="too-low"),
        pytest.param(31.5, id="too-high"),
        pytest.param(24.25, id="quarter-degree"),
    ],
)
def test_fractional_temperature_limits(temperature: float) -> None:
    """Reject half-degree inputs outside the range and unsupported quarter degrees."""
    with pytest.raises(ValueError, match="temperature"):
        PdPioneerClimateCommand(mode=PdPioneerClimateMode.COOL, temperature=temperature)


@pytest.mark.parametrize(
    "mode,power",
    [
        pytest.param(PdPioneerClimateMode.FAN_ONLY, True, id="fan-only"),
        pytest.param(None, False, id="off"),
    ],
)
def test_placeholder_state_rebuild(
    mode: PdPioneerClimateMode | None, power: bool
) -> None:
    """Neither fan-only nor shutdown carries a user-selected target."""
    sent = PdPioneerClimateCommand(mode=mode, power=power)
    received = PdPioneerClimateCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    state = received.state
    assert state.temperature is None
    assert state.power is not None
    rebuilt = PdPioneerClimateCommand(
        mode=state.mode, power=state.power, temperature=state.temperature
    )
    assert rebuilt.data == received.data


def test_required_setpoint() -> None:
    """Powered cooling needs a target in the even packet."""
    with pytest.raises(ValueError, match="temperature"):
        PdPioneerClimateCommand(mode=PdPioneerClimateMode.COOL)


@pytest.mark.parametrize("power", [True, False])
def test_invalid_placeholder_temperature(power: bool) -> None:
    """Both fan-only and shutdown retain validation of explicit targets."""
    with pytest.raises(ValueError, match="temperature"):
        PdPioneerClimateCommand(
            mode=PdPioneerClimateMode.FAN_ONLY, power=power, temperature=99
        )

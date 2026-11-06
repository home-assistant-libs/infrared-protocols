"""Receiver captures, held keys and the timing distortions reported in review."""

from collections.abc import Callable

import pytest

from infrared_protocols.codes.hob2hood.hood import Hob2HoodCode
from infrared_protocols.commands import Command
from infrared_protocols.commands.beo4 import Beo4Command
from infrared_protocols.commands.canalsat import CanalSatCommand, CanalSatLDCommand
from infrared_protocols.commands.climate import ClimateMode
from infrared_protocols.commands.friedrich import FriedrichCommand
from infrared_protocols.commands.hob2hood import Hob2HoodCommand
from infrared_protocols.commands.kaseikyo import KaseikyoCommand
from infrared_protocols.commands.magiquest import (
    MagiQuestCommand,
    MagiQuestLegacyCommand,
)
from infrared_protocols.commands.marantz_extended import MarantzExtendedCommand
from infrared_protocols.commands.mistral import MistralCommand
from infrared_protocols.commands.mitsubishi import MitsubishiCommand
from infrared_protocols.commands.pioneer import PioneerCommand
from infrared_protocols.commands.rc6 import RC6Command
from infrared_protocols.commands.roomba import RoombaCommand
from infrared_protocols.commands.samsung import Samsung32Command
from infrared_protocols.commands.sony import SonyCommand
from infrared_protocols.commands.toto import TotoCommand


def test_rc6_physical_capture() -> None:
    """Arduino-IRremote src/ir_RC5_RC6.hpp records this mode-0 remote press."""
    # https://github.com/Arduino-IRremote/Arduino-IRremote/blob/master/src/ir_RC5_RC6.hpp
    raw = [
        2700, -850, 550, -800, 550, -350, 550, -350, 550, -800, 1400, -400, 550, -400,
        550, -350, 550, -800, 550, -350, 500, -450, 1000, -750, 1000, -450, 500, -400,
        500, -850, 950, -450, 550, -750, 550,
    ]  # fmt: skip
    received = RC6Command.from_raw_timings(raw)
    assert received is not None
    assert (received.mode, received.address, received.command) == (0, 0xF1, 0x76)


def test_sony_physical_capture() -> None:
    """Arduino-IRremote's Sony20 example has stretched marks and 400-us spaces."""
    # https://github.com/Arduino-IRremote/Arduino-IRremote/blob/master/src/ir_Sony.hpp
    raw = [
        2550, -400, 1300, -450, 1350, -450, 1300, -450, 700, -450, 700, -450, 750,
        -450, 700, -400, 1300, -500, 700, -450, 700, -450, 1300, -500, 1300, -450,
        1300, -450, 700, -450, 1350, -400, 750, -450, 700, -450, 1300, -450, 700,
        -450, 700,
    ]  # fmt: skip
    received = SonyCommand.from_raw_timings(raw)
    assert received is not None
    assert (received.address_bits, received.address, received.command) == (13, 0x4B9, 7)


@pytest.mark.parametrize("scale", [0.88, 0.9, 0.92, 1.1, 1.12, 1.15])
@pytest.mark.parametrize("address", [0, 31])
@pytest.mark.parametrize("command", [0, 63, 64, 127])
@pytest.mark.parametrize("extension", [0, 63])
def test_marantz_clock_skew(
    scale: float, address: int, command: int, extension: int
) -> None:
    """The long pause must not shift all subsequent Manchester cells."""
    sent = MarantzExtendedCommand(address=address, command=command, extension=extension)
    received = MarantzExtendedCommand.from_raw_timings(
        [round(t * scale) for t in sent.get_raw_timings()] + [-5000]
    )
    assert received is not None
    assert (received.address, received.command, received.extension) == (
        address,
        command,
        extension,
    )


@pytest.mark.parametrize(
    "command",
    [
        pytest.param(
            KaseikyoCommand(address=0x2002, data=b"\xa0\x01\xff"), id="kaseikyo"
        ),
        pytest.param(
            MitsubishiCommand(mode=ClimateMode.COOL, temperature=23), id="mitsubishi"
        ),
        pytest.param(
            FriedrichCommand(mode=ClimateMode.COOL, temperature_f=72),
            id="friedrich-aeha",
        ),
        pytest.param(
            MistralCommand(mode=ClimateMode.COOL, temperature=23), id="mistral-aeha"
        ),
        pytest.param(Samsung32Command(address=7, command=2), id="samsung"),
        pytest.param(PioneerCommand(address=7, command=2), id="pioneer"),
    ],
)
@pytest.mark.parametrize("skew", [-100, 100, 150, 200])
def test_receiver_mark_space_bias(
    command: KaseikyoCommand
    | MitsubishiCommand
    | FriedrichCommand
    | MistralCommand
    | Samsung32Command
    | PioneerCommand,
    skew: int,
) -> None:
    """A demodulator adds time to marks and removes the same time from spaces."""
    received = type(command).from_raw_timings(
        [t + skew for t in command.get_raw_timings()]
    )
    assert received is not None
    assert received.get_raw_timings() == command.get_raw_timings()


@pytest.mark.parametrize(
    "command,decoder",
    [
        pytest.param(
            RoombaCommand(data=0x88), RoombaCommand.from_raw_timings, id="roomba"
        ),
        pytest.param(
            MagiQuestCommand(wand_id=0x12345678, magnitude=0x123),
            MagiQuestCommand.from_raw_timings,
            id="magiquest",
        ),
    ],
)
def test_last_bit_space_merges_idle(
    command: Command, decoder: Callable[[list[int]], Command | None]
) -> None:
    """The final bit is determined by its mark, not the capture's idle timeout."""
    received = decoder(command.get_raw_timings()[:-1] + [-20000])
    assert received is not None
    assert received.get_raw_timings() == command.get_raw_timings()


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


def test_sony_held_key() -> None:
    """SIRC repeats a full frame on a 45-ms period."""
    sent = SonyCommand(address=0x4B9, address_bits=13, command=7, repeat_count=2)
    received = SonyCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert (received.address, received.command, received.repeat_count) == (0x4B9, 7, 2)


@pytest.mark.parametrize("scale", [0.7, 1.3])
def test_samsung_scaled_and_partial_repeat(scale: float) -> None:
    """A complete command survives a clipped final held-key repeat."""
    raw = Samsung32Command(address=7, command=2, repeat_count=1).get_raw_timings()[:-10]
    received = Samsung32Command.from_raw_timings([round(t * scale) for t in raw])
    assert received is not None
    assert (received.address, received.command, received.repeat_count) == (7, 2, 0)


def test_magiquest_legacy_fields() -> None:
    """The deployed legacy payload has its own complete receiver."""
    sent = MagiQuestLegacyCommand(wand_id=0x12345678, magnitude=0xABCD)
    received = MagiQuestLegacyCommand.from_raw_timings(sent.get_raw_timings())
    assert received is not None
    assert (received.wand_id, received.magnitude) == (0x12345678, 0xABCD)


def test_toto_three_transmissions() -> None:
    """A Toto button always transmits three copies 36 ms apart."""
    sent = TotoCommand(command=0xED, rc_code_1=3, rc_code_2=9)
    raw = sent.get_raw_timings()
    assert raw.count(-36000) == 2
    received = TotoCommand.from_raw_timings(raw)
    assert received is not None
    assert (received.command, received.rc_code_1, received.rc_code_2) == (0xED, 3, 9)


def test_beolink_repeated_capture() -> None:
    """The link bit is data and multiple identical frames are accepted."""
    sent = Beo4Command(source=0x12, command=0xA5, link=True)
    raw = sent.get_raw_timings()
    received = Beo4Command.from_raw_timings(raw + [-30000] + raw)
    assert received is not None
    assert received.link
    assert (received.source, received.command, received.received_frames) == (
        0x12,
        0xA5,
        2,
    )


@pytest.mark.parametrize(
    "encoder,decoder",
    [
        pytest.param(CanalSatCommand, CanalSatLDCommand, id="standard-is-not-ld"),
        pytest.param(CanalSatLDCommand, CanalSatCommand, id="ld-is-not-standard"),
    ],
)
def test_canalsat_nominal_variants(
    encoder: type[CanalSatCommand], decoder: type[CanalSatCommand]
) -> None:
    """Nominal clocks do not get mislabeled as the other carrier variant."""
    assert (
        decoder.from_raw_timings(
            encoder(device=0x12, address=0x23, command=0x56).get_raw_timings()
        )
        is None
    )


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
def test_hob_dropped_final_space(code: Hob2HoodCode) -> None:
    """Some receivers stop before reporting the final space."""
    received = Hob2HoodCommand.from_raw_timings(
        code.to_command().get_raw_timings()[:-1]
    )
    assert received is not None
    assert received.command == code


def test_hob_unknown_command() -> None:
    """Only the seven supported hood actions can be encoded."""
    with pytest.raises(ValueError):
        Hob2HoodCommand(command=0)

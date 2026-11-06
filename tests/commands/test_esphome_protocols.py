"""Independent Python implementations checked against recorded ESPHome outputs."""

import json
from collections.abc import Callable
from pathlib import Path

import pytest

from infrared_protocols.codes.gobox.remote import GoboxCode
from infrared_protocols.codes.hob2hood.hood import Hob2HoodCode
from infrared_protocols.commands import Command
from infrared_protocols.commands.beo4 import Beo4Command
from infrared_protocols.commands.canalsat import CanalSatCommand, CanalSatLDCommand
from infrared_protocols.commands.coolix import CoolixCommand
from infrared_protocols.commands.dish import DishCommand
from infrared_protocols.commands.dyson import DysonCommand
from infrared_protocols.commands.gobox import GoboxCommand
from infrared_protocols.commands.haier import HaierCommand
from infrared_protocols.commands.hob2hood import Hob2HoodCommand
from infrared_protocols.commands.ira211 import (
    Ira211Action,
    Ira211Command,
    Ira211Fan,
    Ira211Mode,
)
from infrared_protocols.commands.jvc import JvcCommand
from infrared_protocols.commands.lg import Lg28Command, Lg32Command
from infrared_protocols.commands.magiquest import (
    MagiQuestCommand,
    MagiQuestLegacyCommand,
)
from infrared_protocols.commands.midea import MideaCommand
from infrared_protocols.commands.mirage import MirageCommand
from infrared_protocols.commands.pd_pioneer import PdPioneerCommand
from infrared_protocols.commands.pioneer_wyt import PioneerWytCommand
from infrared_protocols.commands.roomba import RoombaCommand
from infrared_protocols.commands.samsung36 import Samsung36Command
from infrared_protocols.commands.toshiba_ac import ToshibaAcPacketCommand
from infrared_protocols.commands.toto import TotoCommand

Decoder = Callable[[list[int]], Command | None]
_INPUTS: list[tuple[str, Command, Decoder]] = [
    ("dyson", DysonCommand(code=0x1234, index=2), DysonCommand.from_raw_timings),
    ("lg28", Lg28Command(data=0xABCDEFA), Lg28Command.from_raw_timings),
    ("lg32", Lg32Command(data=0xABCDEFAB), Lg32Command.from_raw_timings),
    *[
        (
            f"ira211_{int(action)}",
            Ira211Command(
                action=action,
                temperature=21.5,
                mode=Ira211Mode.TIMER,
                fan=Ira211Fan.HIGH,
            ),
            Ira211Command.from_raw_timings,
        )
        for action in Ira211Action
    ],
    ("jvc", JvcCommand(data=0xA55A), JvcCommand.from_raw_timings),
    ("dish", DishCommand(address=4, command=37), DishCommand.from_raw_timings),
    (
        "samsung36",
        Samsung36Command(address=0x1234, command=0xABCDE),
        Samsung36Command.from_raw_timings,
    ),
    (
        "toto",
        TotoCommand(rc_code_1=3, rc_code_2=9, command=0xED),
        TotoCommand.from_raw_timings,
    ),
    ("roomba", RoombaCommand(data=0xA5), RoombaCommand.from_raw_timings),
    ("hob2hood", Hob2HoodCommand(command=0x6F), Hob2HoodCommand.from_raw_timings),
    ("gobox", GoboxCommand(code=0xAA55), GoboxCommand.from_raw_timings),
    ("beo4", Beo4Command(source=0x12, command=0xA5), Beo4Command.from_raw_timings),
    (
        "canalsat",
        CanalSatCommand(device=0x12, address=0x23, command=0x56),
        CanalSatCommand.from_raw_timings,
    ),
    (
        "canalsatld",
        CanalSatLDCommand(device=0x12, address=0x23, command=0x56),
        CanalSatLDCommand.from_raw_timings,
    ),
    (
        "haier",
        HaierCommand(data=bytes([0xA5, 1, 2, 3, 4, 5, 6, 7])),
        HaierCommand.from_raw_timings,
    ),
    (
        "mirage",
        MirageCommand(data=bytes([0xA5, *range(1, 14)])),
        MirageCommand.from_raw_timings,
    ),
    (
        "midea",
        MideaCommand(data=bytes.fromhex("a18148ffff")),
        MideaCommand.from_raw_timings,
    ),
    (
        "coolix",
        CoolixCommand(first=0xB21FC8, second=0xB2BFE4),
        CoolixCommand.from_raw_timings,
    ),
    (
        "pd_pioneer",
        PdPioneerCommand(data=bytes.fromhex("23cb2601002403070580000000")),
        PdPioneerCommand.from_raw_timings,
    ),
    (
        "pioneer_wyt",
        PioneerWytCommand(data=bytes.fromhex("23cb2602002403070580000000")),
        PioneerWytCommand.from_raw_timings,
    ),
    (
        "toshiba_ac",
        ToshibaAcPacketCommand(rc_code_1=0x123456789ABC, rc_code_2=0xABCDEF012345),
        ToshibaAcPacketCommand.from_raw_timings,
    ),
]
SIGNALS = {
    entry["protocol"]: entry
    for entry in json.loads(
        (Path(__file__).parents[1] / "fixtures/esphome_protocols.json").read_text()
    )["signals"]
}


CASES = [
    pytest.param(name, command, decode, id=name) for name, command, decode in _INPUTS
]
ENCODERS = [pytest.param(command, decode, id=name) for name, command, decode in _INPUTS]


@pytest.mark.parametrize("name,command,decode", CASES)
def test_reference_signals(name: str, command: Command, decode: Decoder) -> None:
    """Match independent upstream encoder output and decode it without data loss."""
    fixture = SIGNALS[name]
    assert command.get_raw_timings() == fixture["timings"]
    assert command.modulation == fixture["carrier"]
    decoded = decode(fixture["timings"])
    assert decoded is not None
    assert decoded.get_raw_timings() == fixture["timings"]


@pytest.mark.parametrize("command,decode", ENCODERS)
@pytest.mark.parametrize("prefix", [0, 1, 3, 7])
def test_truncated_frames(command: Command, decode: Decoder, prefix: int) -> None:
    """Incomplete fields must not produce commands."""
    assert decode(command.get_raw_timings()[:prefix]) is None


@pytest.mark.parametrize("command,decode", ENCODERS)
def test_invalid_polarity(command: Command, decode: Decoder) -> None:
    """A mark in place of a space is not a valid signal."""
    raw = command.get_raw_timings()
    raw[1] = abs(raw[1])
    assert decode(raw) is None


@pytest.mark.parametrize("command,decode", ENCODERS)
@pytest.mark.parametrize("scale", [0.92, 1.08])
def test_receiver_jitter(command: Command, decode: Decoder, scale: float) -> None:
    """Small timing distortion should not change the decoded message."""
    raw = [round(value * scale) for value in command.get_raw_timings()]
    decoded = decode(raw)
    assert decoded is not None
    assert decoded.get_raw_timings() == command.get_raw_timings()


@pytest.mark.parametrize("code", list(Hob2HoodCode))
def test_hob2hood_codes(code: Hob2HoodCode) -> None:
    """Every named extractor command decodes back to its command byte."""
    command = code.to_command()
    decoded = Hob2HoodCommand.from_raw_timings(command.get_raw_timings())
    assert decoded is not None
    assert decoded.command == code.value


@pytest.mark.parametrize("code", list(GoboxCode))
def test_gobox_codes(code: GoboxCode) -> None:
    """Every named remote button decodes back to its code."""
    decoded = GoboxCommand.from_raw_timings(code.to_command().get_raw_timings())
    assert decoded is not None
    assert decoded.code == code.value


def test_magiquest_legacy_reference() -> None:
    """The legacy transmitter layout remains distinct from physical wand frames."""
    command = MagiQuestLegacyCommand(wand_id=0x12345678, magnitude=0xABCD)
    assert command.get_raw_timings() == SIGNALS["magiquest_legacy"]["timings"]
    assert MagiQuestCommand.from_raw_timings(command.get_raw_timings()) is None


@pytest.mark.parametrize(
    "wand_id,magnitude", [(0, 0), (0x12345678, 0x123), (0x7FFFFFFF, 511)]
)
@pytest.mark.parametrize("trim", [0, 1])
def test_magiquest_wand(wand_id: int, magnitude: int, trim: int) -> None:
    """Decode complete wand messages with an optional final space."""
    command = MagiQuestCommand(wand_id=wand_id, magnitude=magnitude)
    raw = command.get_raw_timings()
    decoded = MagiQuestCommand.from_raw_timings(raw[: len(raw) - trim])
    assert decoded is not None
    assert (decoded.wand_id, decoded.magnitude) == (wand_id, magnitude)


def test_magiquest_checksum() -> None:
    """A changed checksum symbol must be rejected."""
    raw = MagiQuestCommand(wand_id=0x12345678, magnitude=0x123).get_raw_timings()
    raw[-2:] = [576, -576]
    assert MagiQuestCommand.from_raw_timings(raw) is None


@pytest.mark.parametrize("action", list(Ira211Action))
@pytest.mark.parametrize("temperature", [5, 20.5, 35])
def test_ira211_actions(action: Ira211Action, temperature: float) -> None:
    """Every action carries exactly its own fields."""
    command = Ira211Command(
        action=action,
        temperature=temperature,
        mode=Ira211Mode.TIMER,
        fan=Ira211Fan.HIGH,
    )
    decoded = Ira211Command.from_raw_timings(command.get_raw_timings())
    assert decoded is not None
    assert decoded.get_raw_timings() == command.get_raw_timings()


@pytest.mark.parametrize(
    "decode,raw",
    [
        pytest.param(TotoCommand.from_raw_timings, [6000, -3000], id="toto-header"),
        pytest.param(
            MideaCommand.from_raw_timings,
            MideaCommand(data=bytes(5)).get_raw_timings()[:99],
            id="midea-incomplete",
        ),
        pytest.param(
            ToshibaAcPacketCommand.from_raw_timings,
            ToshibaAcPacketCommand(rc_code_1=1).get_raw_timings()[:99],
            id="toshiba-missing-copy",
        ),
    ],
)
def test_required_fields_and_copies(decode: Decoder, raw: list[int]) -> None:
    """Headers alone and missing compulsory copies cannot become commands."""
    assert decode(raw) is None

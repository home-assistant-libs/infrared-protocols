"""Decoder coverage for existing encoders, framing errors and held keys."""

from collections.abc import Callable
from itertools import product

import pytest

from infrared_protocols.commands import Command
from infrared_protocols.commands.aeha import AehaCommand
from infrared_protocols.commands.dyson import DysonAm09Command, DysonCoolCommand
from infrared_protocols.commands.kaseikyo import KaseikyoCommand
from infrared_protocols.commands.marantz_extended import MarantzExtendedCommand
from infrared_protocols.commands.panasonic_ac import (
    PanasonicAcCommand,
    PanasonicAcMode,
    PanasonicAcModel,
    PanasonicAcToggle,
    PanasonicAcToggleCommand,
)
from infrared_protocols.commands.pioneer import PioneerCommand
from infrared_protocols.commands.rc5 import RC5Command
from infrared_protocols.commands.rc6 import RC6Command
from infrared_protocols.commands.samsung import Samsung32Command
from infrared_protocols.commands.sony import SonyCommand

Decoder = Callable[[list[int]], Command | None]
_INPUTS: list[tuple[Command, Decoder]] = [
    *[
        (
            RC5Command(address=a, command=c, toggle=t, repeat_count=r),
            RC5Command.from_raw_timings,
        )
        for a, c, t, r in product((0, 31), (0, 63, 64, 127), (0, 1), (0, 2))
    ],
    *[
        (
            RC6Command(address=a, command=c, toggle=t, repeat_count=r, mode=m),
            RC6Command.from_raw_timings,
        )
        for a, c, t, r, m in product((0, 255), (0, 255), (0, 1), (0, 2), (0, 1, 6, 7))
    ],
    *[
        (
            MarantzExtendedCommand(
                address=a, command=c, extension=e, toggle=t, repeat_count=r
            ),
            MarantzExtendedCommand.from_raw_timings,
        )
        for a, c, e, t, r in product((0, 31), (0, 64, 127), (0, 63), (0, 1), (0, 2))
    ],
    *[
        (
            SonyCommand(address=(1 << b) - 1, address_bits=b, command=c),
            SonyCommand.from_raw_timings,
        )
        for b, c in product((5, 8, 13), (0, 127))
    ],
    *[
        (
            Samsung32Command(address=a, command=c, repeat_count=r),
            Samsung32Command.from_raw_timings,
        )
        for a, c, r in product((0, 255, 256, 65535), (0, 255), (0, 2))
    ],
    *[
        (
            KaseikyoCommand(address=a, data=d, repeat_count=r),
            KaseikyoCommand.from_raw_timings,
        )
        for a, d, r in product(
            (0, 0x2002, 65535),
            (bytes([0]), bytes([0xA0, 1, 255]), [bytes([0xA0, 1]), bytes([0xB0, 255])]),
            (0, 2),
        )
    ],
    *[
        (
            PioneerCommand(
                address=0xA5,
                command=128,
                preamble_address=a,
                preamble_command=c,
                repeat_count=r,
            ),
            PioneerCommand.from_raw_timings,
        )
        for a, c, r in product((0, 255), (0, 255), (0, 2))
    ],
    *[
        (cls(code=c), cls.from_raw_timings)
        for cls, c in product((DysonCoolCommand, DysonAm09Command), (0, 1, 255))
    ],
    (AehaCommand(data=bytes.fromhex("23cb2601")), AehaCommand.from_raw_timings),
    (
        PanasonicAcCommand(mode=PanasonicAcMode.COOL, temperature=24),
        PanasonicAcCommand.from_raw_timings,
    ),
    *[
        (PanasonicAcToggleCommand(toggle=t), PanasonicAcToggleCommand.from_raw_timings)
        for t in PanasonicAcToggle
    ],
]


CASES = [
    pytest.param(command, decode, id=name)
    for (command, decode), name in zip(
        _INPUTS,
        [
            type(command).__name__
            + "-"
            + "-".join(
                f"{key}={value}"
                for key, value in vars(command).items()
                if key
                in (
                    "address",
                    "command",
                    "extension",
                    "toggle",
                    "mode",
                    "data",
                    "code",
                    "payload",
                    "repeat_count",
                    "address_bits",
                    "preamble_address",
                    "preamble_command",
                )
            )
            for command, _ in _INPUTS
        ],
        strict=True,
    )
]


@pytest.mark.parametrize("command,decode", CASES)
def test_decode_existing_encoder(command: Command, decode: Decoder) -> None:
    """Recover edge-valued fields, extensions, toggles and full-frame repeats."""
    raw = command.get_raw_timings()
    result = decode(raw)
    assert result is not None
    assert result.get_raw_timings() == raw


@pytest.mark.parametrize("command,decode", CASES)
@pytest.mark.parametrize("prefix", [0, 1, 5])
def test_truncated(command: Command, decode: Decoder, prefix: int) -> None:
    """A partial leader or payload cannot be a complete command."""
    assert decode(command.get_raw_timings()[:prefix]) is None


@pytest.mark.parametrize(
    "model", [m for m in PanasonicAcModel if m != PanasonicAcModel.CKP]
)
def test_panasonic_named_models(model: PanasonicAcModel) -> None:
    """The caller's remote model survives decoding a valid full state."""
    command = PanasonicAcCommand(model=model, mode=PanasonicAcMode.HEAT, temperature=21)
    result = PanasonicAcCommand.from_raw_timings(command.get_raw_timings(), model=model)
    assert result is not None
    assert result.get_raw_timings() == command.get_raw_timings()


def test_panasonic_power_toggle() -> None:
    """A CKP power request retains the toggle bit."""
    command = PanasonicAcCommand(
        model=PanasonicAcModel.CKP,
        mode=PanasonicAcMode.HEAT,
        temperature=21,
        power_toggle=True,
    )
    result = PanasonicAcCommand.from_raw_timings(
        command.get_raw_timings(), model=PanasonicAcModel.CKP
    )
    assert result is not None
    assert result.get_raw_timings() == command.get_raw_timings()


@pytest.mark.parametrize(
    "factory,decode",
    [
        (
            lambda: RC5Command(address=1, command=2, repeat_count=1),
            RC5Command.from_raw_timings,
        ),
        (
            lambda: RC6Command(address=1, command=2, repeat_count=1),
            RC6Command.from_raw_timings,
        ),
        (
            lambda: Samsung32Command(address=1, command=2, repeat_count=1),
            Samsung32Command.from_raw_timings,
        ),
    ],
    ids=["rc5", "rc6", "samsung32"],
)
def test_invalid_repeat_period(factory: Callable[[], Command], decode: Decoder) -> None:
    """An unrelated frame after a long pause is not a held-key repeat."""
    raw = factory().get_raw_timings()
    index = raw.index(min(raw))
    raw[index] *= 3
    assert decode(raw) is None

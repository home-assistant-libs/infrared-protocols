"""Known Anthem MRX/AVM models and the IR codes each one accepts."""

from __future__ import annotations

from dataclasses import dataclass

from .mrx_x20_x40_avm_x import AnthemCode


@dataclass(frozen=True, slots=True)
class AnthemModel:
    """An Anthem MRX/AVM model and the IR codes it accepts."""

    name: str
    codes: frozenset[AnthemCode]


# Common code sets reused across models.

_BASE = frozenset(
    {
        AnthemCode.POWER,
        AnthemCode.STANDBY,
        AnthemCode.BASS,
        AnthemCode.DIM,
        AnthemCode.BALANCE,
        AnthemCode.TREBLE,
        AnthemCode.LEVEL,
        AnthemCode.NUM_1,
        AnthemCode.NUM_2,
        AnthemCode.NUM_3,
        AnthemCode.NUM_4,
        AnthemCode.NUM_5,
        AnthemCode.NUM_6,
        AnthemCode.NUM_7,
        AnthemCode.NUM_8,
        AnthemCode.NUM_9,
        AnthemCode.NUM_0,
        AnthemCode.PRESET,
        AnthemCode.INPUT_CYCLE,
        AnthemCode.SETUP_MENU,
        AnthemCode.INFO,
        AnthemCode.CURSOR_LEFT,
        AnthemCode.CURSOR_UP,
        AnthemCode.SELECT,
        AnthemCode.CURSOR_RIGHT,
        AnthemCode.CURSOR_DOWN,
        AnthemCode.CLEAR,
        AnthemCode.DYNAMICS,
        AnthemCode.MODE,
        AnthemCode.LAST,
        AnthemCode.VOLUME_UP,
        AnthemCode.VOLUME_DOWN,
        AnthemCode.MUTE,
        AnthemCode.LIP_SYNC,
        AnthemCode.PAGE_PRESET_UP,
        AnthemCode.PAGE_PRESET_DOWN,
        AnthemCode.INPUT_1,
        AnthemCode.INPUT_2,
        AnthemCode.INPUT_3,
        AnthemCode.INPUT_4,
        AnthemCode.INPUT_5,
        AnthemCode.INPUT_6,
        AnthemCode.INPUT_7,
        AnthemCode.INPUT_8,
        AnthemCode.INPUT_9,
        AnthemCode.INPUT_10,
        AnthemCode.INPUT_11,
        AnthemCode.INPUT_12,
        AnthemCode.INPUT_13,
        AnthemCode.INPUT_14,
        AnthemCode.INPUT_15,
        AnthemCode.INPUT_16,
        AnthemCode.INPUT_17,
        AnthemCode.INPUT_18,
        AnthemCode.INPUT_19,
        AnthemCode.INPUT_20,
        AnthemCode.ZONE2_POWER,
        AnthemCode.ZONE2_STANDBY,
        AnthemCode.ZONE2_VOLUME_UP,
        AnthemCode.ZONE2_VOLUME_DOWN,
        AnthemCode.ZONE2_MUTE,
        AnthemCode.ZONE2_INPUT_CYCLE,
        AnthemCode.ZONE2_PRESET_UP,
        AnthemCode.ZONE2_PRESET_DOWN,
        AnthemCode.ZONE2_INPUT_1,
        AnthemCode.ZONE2_INPUT_2,
        AnthemCode.ZONE2_INPUT_3,
        AnthemCode.ZONE2_INPUT_4,
        AnthemCode.ZONE2_INPUT_5,
        AnthemCode.ZONE2_INPUT_6,
        AnthemCode.ZONE2_INPUT_7,
        AnthemCode.ZONE2_INPUT_8,
        AnthemCode.ZONE2_INPUT_9,
        AnthemCode.ZONE2_INPUT_10,
        AnthemCode.ZONE2_INPUT_11,
        AnthemCode.ZONE2_INPUT_12,
        AnthemCode.ZONE2_INPUT_13,
        AnthemCode.ZONE2_INPUT_14,
        AnthemCode.ZONE2_INPUT_15,
        AnthemCode.ZONE2_INPUT_16,
        AnthemCode.ZONE2_INPUT_17,
        AnthemCode.ZONE2_INPUT_18,
        AnthemCode.ZONE2_INPUT_19,
        AnthemCode.ZONE2_INPUT_20,
    }
)

#: Inputs 21-30. Per Anthem's documentation, the factory MRX x10 remote does
#: not include these -- they exist for programmable remotes on MRX x20, AVM 60,
#: and the newer MRX x40 / AVM 70 / AVM 90 generation including 4K and 8k models.
_EXTENDED_INPUTS = frozenset(
    {
        AnthemCode.INPUT_21,
        AnthemCode.INPUT_22,
        AnthemCode.INPUT_23,
        AnthemCode.INPUT_24,
        AnthemCode.INPUT_25,
        AnthemCode.INPUT_26,
        AnthemCode.INPUT_27,
        AnthemCode.INPUT_28,
        AnthemCode.INPUT_29,
        AnthemCode.INPUT_30,
        AnthemCode.ZONE2_INPUT_21,
        AnthemCode.ZONE2_INPUT_22,
        AnthemCode.ZONE2_INPUT_23,
        AnthemCode.ZONE2_INPUT_24,
        AnthemCode.ZONE2_INPUT_25,
        AnthemCode.ZONE2_INPUT_26,
        AnthemCode.ZONE2_INPUT_27,
        AnthemCode.ZONE2_INPUT_28,
        AnthemCode.ZONE2_INPUT_29,
        AnthemCode.ZONE2_INPUT_30,
    }
)


GENERIC = AnthemModel(
    name="Generic Anthem MRX/AVM",
    codes=frozenset(AnthemCode),
)


MRX_310 = AnthemModel(name="MRX 310", codes=_BASE)
MRX_510 = AnthemModel(name="MRX 510", codes=_BASE)
MRX_710 = AnthemModel(name="MRX 710", codes=_BASE)

MRX_520 = AnthemModel(name="MRX 520", codes=_BASE | _EXTENDED_INPUTS)
MRX_720 = AnthemModel(name="MRX 720", codes=_BASE | _EXTENDED_INPUTS)
MRX_1120 = AnthemModel(name="MRX 1120", codes=_BASE | _EXTENDED_INPUTS)
AVM_60 = AnthemModel(name="AVM 60", codes=_BASE | _EXTENDED_INPUTS)

MRX_540 = AnthemModel(name="MRX 540", codes=_BASE | _EXTENDED_INPUTS)
MRX_740 = AnthemModel(name="MRX 740", codes=_BASE | _EXTENDED_INPUTS)
MRX_1140 = AnthemModel(name="MRX 1140", codes=_BASE | _EXTENDED_INPUTS)
AVM_70 = AnthemModel(name="AVM 70", codes=_BASE | _EXTENDED_INPUTS)
AVM_90 = AnthemModel(name="AVM 90", codes=_BASE | _EXTENDED_INPUTS)


#: All known Anthem MRX/AVM models, for iteration. Generic is first so
#: integrations using this list as a UI source default to the catch-all.
ALL_MODELS: tuple[AnthemModel, ...] = (
    GENERIC,
    MRX_310,
    MRX_510,
    MRX_710,
    MRX_520,
    MRX_720,
    MRX_1120,
    AVM_60,
    MRX_540,
    MRX_740,
    MRX_1140,
    AVM_70,
    AVM_90,
)

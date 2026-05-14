"""Known Marantz audio models and the IR codes each one accepts."""

from __future__ import annotations

from dataclasses import dataclass

from .audio import MarantzAudioCode


@dataclass(frozen=True, slots=True)
class MarantzModel:
    """A Marantz audio model and the IR codes it accepts."""

    name: str
    codes: frozenset[MarantzAudioCode]


# Common code sets reused across models.

_STANDARD_AUDIO = frozenset(
    {
        MarantzAudioCode.POWER,
        MarantzAudioCode.POWER_ON,
        MarantzAudioCode.POWER_OFF,
        MarantzAudioCode.MUTE,
        MarantzAudioCode.MUTE_ON,
        MarantzAudioCode.MUTE_OFF,
        MarantzAudioCode.VOLUME_UP,
        MarantzAudioCode.VOLUME_DOWN,
    }
)

_TONE_CONTROLS = frozenset(
    {
        MarantzAudioCode.BASS_UP,
        MarantzAudioCode.BASS_DOWN,
        MarantzAudioCode.TREBLE_UP,
        MarantzAudioCode.TREBLE_DOWN,
    }
)

_CURSOR_PAD = frozenset(
    {
        MarantzAudioCode.CURSOR_UP,
        MarantzAudioCode.CURSOR_DOWN,
        MarantzAudioCode.CURSOR_LEFT,
        MarantzAudioCode.CURSOR_RIGHT,
        MarantzAudioCode.CURSOR_OK,
    }
)


GENERIC = MarantzModel(
    name="Generic Amplifier",
    codes=frozenset(MarantzAudioCode),
)


PM6006 = MarantzModel(
    name="PM6006 Integrated Amplifier",
    codes=_STANDARD_AUDIO
    | frozenset(
        {
            MarantzAudioCode.SPEAKER_AB,
            MarantzAudioCode.SOURCE_DIRECT,
            MarantzAudioCode.LOUDNESS,
            MarantzAudioCode.SOURCE_CD,
            MarantzAudioCode.SOURCE_CDR,
            MarantzAudioCode.SOURCE_PHONO,
            MarantzAudioCode.SOURCE_TUNER,
            MarantzAudioCode.SOURCE_OPTICAL,
            MarantzAudioCode.SOURCE_COAX,
            MarantzAudioCode.SOURCE_NETWORK,
        }
    ),
)

RC042SR = MarantzModel(
    name="RC042SR Audio Receiver",
    codes=_STANDARD_AUDIO
    | frozenset(
        {
            MarantzAudioCode.SLEEP,
            MarantzAudioCode.CURSOR_UP,
            MarantzAudioCode.CURSOR_DOWN,
            MarantzAudioCode.CURSOR_LEFT,
            MarantzAudioCode.CURSOR_RIGHT,
            MarantzAudioCode.CURSOR_ENTER,
            MarantzAudioCode.SOURCE_TV,
            MarantzAudioCode.SOURCE_VCR1,
            MarantzAudioCode.SOURCE_SAT,
            MarantzAudioCode.SOURCE_TUNER,
            MarantzAudioCode.SOURCE_CD,
            MarantzAudioCode.SOURCE_PHONO,
        }
    ),
)

SR_19 = MarantzModel(
    name="SR-19 Receiver",
    codes=_STANDARD_AUDIO
    | frozenset(
        {
            MarantzAudioCode.SOURCE_TUNER,
            MarantzAudioCode.TUNER_FM,
            MarantzAudioCode.TUNER_AM,
            MarantzAudioCode.TUNER_LW,
            MarantzAudioCode.TUNER_PRESET_UP,
            MarantzAudioCode.TUNER_PRESET_DOWN,
            MarantzAudioCode.TUNER_MEMORY,
            MarantzAudioCode.TUNER_CLEAR,
        }
    ),
)

SR_7000 = MarantzModel(
    name="SR-7000 Receiver",
    codes=_STANDARD_AUDIO
    | _TONE_CONTROLS
    | _CURSOR_PAD
    | frozenset(
        {
            MarantzAudioCode.DISPLAY,
            MarantzAudioCode.SLEEP,
            MarantzAudioCode.DSP_MODE,
            MarantzAudioCode.CHANNEL_UP,
            MarantzAudioCode.CHANNEL_DOWN,
            MarantzAudioCode.TUNER_MEMORY,
            MarantzAudioCode.TUNER_CLEAR,
        }
    ),
)

SR_7200 = MarantzModel(
    name="SR7200 Receiver",
    codes=_STANDARD_AUDIO
    | _TONE_CONTROLS
    | _CURSOR_PAD
    | frozenset(
        {
            MarantzAudioCode.DISPLAY,
            MarantzAudioCode.SLEEP,
            MarantzAudioCode.CHANNEL_UP,
            MarantzAudioCode.CHANNEL_DOWN,
            MarantzAudioCode.TUNER_MEMORY,
            MarantzAudioCode.TUNER_CLEAR,
        }
    ),
)

SR_7300 = MarantzModel(
    name="SR-7300 Receiver",
    codes=_STANDARD_AUDIO
    | _TONE_CONTROLS
    | _CURSOR_PAD
    | frozenset(
        {
            MarantzAudioCode.SLEEP,
            MarantzAudioCode.DISPLAY,
            MarantzAudioCode.SPEAKER_AB,
            MarantzAudioCode.CURSOR_EXIT,
            MarantzAudioCode.CHANNEL_UP,
            MarantzAudioCode.CHANNEL_DOWN,
            MarantzAudioCode.INPUT,
            MarantzAudioCode.SOURCE_TV,
            MarantzAudioCode.SOURCE_VCR1,
            MarantzAudioCode.SOURCE_SAT,
            MarantzAudioCode.SOURCE_TUNER,
            MarantzAudioCode.SOURCE_CD,
            MarantzAudioCode.SOURCE_CDR,
            MarantzAudioCode.SOURCE_MD,
            MarantzAudioCode.SOURCE_TAPE,
        }
    ),
)

SR_670 = MarantzModel(
    name="SR670 Receiver",
    codes=_STANDARD_AUDIO
    | frozenset(
        {
            MarantzAudioCode.SLEEP,
            MarantzAudioCode.DSP_MODE,
            MarantzAudioCode.DELAY,
            MarantzAudioCode.INPUT_CYCLE,
            MarantzAudioCode.SURROUND_UP,
            MarantzAudioCode.SURROUND_DOWN,
            MarantzAudioCode.CENTER_LEVEL_UP,
            MarantzAudioCode.CENTER_LEVEL_DOWN,
            MarantzAudioCode.SOURCE_TV,
            MarantzAudioCode.SOURCE_LD,
            MarantzAudioCode.SOURCE_VCR1,
            MarantzAudioCode.SOURCE_SAT,
            MarantzAudioCode.SOURCE_TUNER,
            MarantzAudioCode.SOURCE_CD,
            MarantzAudioCode.SOURCE_TAPE,
            MarantzAudioCode.SOURCE_MD,
        }
    ),
)

AV_9000 = MarantzModel(
    name="AV-9000 Receiver",
    codes=_STANDARD_AUDIO
    | _TONE_CONTROLS
    | _CURSOR_PAD
    | frozenset(
        {
            MarantzAudioCode.DISPLAY,
            MarantzAudioCode.SLEEP,
            MarantzAudioCode.DSP_MODE,
            MarantzAudioCode.SOURCE_DIRECT,
            MarantzAudioCode.FAST_FORWARD,
            MarantzAudioCode.REWIND,
            MarantzAudioCode.CHANNEL_UP,
            MarantzAudioCode.CHANNEL_DOWN,
            MarantzAudioCode.TUNER_FM,
            MarantzAudioCode.TUNER_AM,
            MarantzAudioCode.TUNER_MODE,
            MarantzAudioCode.TUNER_SCAN,
            MarantzAudioCode.TUNER_MEMORY,
            MarantzAudioCode.TUNER_CLEAR,
            MarantzAudioCode.SOURCE_PHONO,
            MarantzAudioCode.SOURCE_TV,
            MarantzAudioCode.SOURCE_LD,
            MarantzAudioCode.SOURCE_VCR1,
            MarantzAudioCode.SOURCE_SAT,
            MarantzAudioCode.SOURCE_TUNER,
            MarantzAudioCode.SOURCE_CD,
            MarantzAudioCode.SOURCE_TAPE,
            MarantzAudioCode.SOURCE_CDR,
        }
    ),
)


#: All known Marantz audio models, for iteration. Generic is first so
#: integrations using this list as a UI source default to the catch-all.
ALL_MODELS: tuple[MarantzModel, ...] = (
    GENERIC,
    PM6006,
    RC042SR,
    SR_19,
    SR_7000,
    SR_7200,
    SR_7300,
    SR_670,
    AV_9000,
)

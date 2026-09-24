"""Tests for the Alpha Bidet model to command-set mapping."""

from infrared_protocols.codes.alpha_bidet.models import (
    MODEL_TO_COMMAND_SET,
    AlphaBidetCommandSet,
    AlphaBidetModel,
)


def test_every_model_maps_to_a_command_set() -> None:
    """A model missing from the map would raise a KeyError at config time."""
    assert set(MODEL_TO_COMMAND_SET) == set(AlphaBidetModel)


def test_every_command_set_is_reachable_from_a_model() -> None:
    """A command set no model selects is dead code the integration can never send."""
    assert set(MODEL_TO_COMMAND_SET.values()) == set(AlphaBidetCommandSet)

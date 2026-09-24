"""Alpha Bidet washlet models, command-set groupings, and their mapping.

Only models whose codes were captured from their own remote are listed.
"""

from enum import StrEnum


class AlphaBidetCommandSet(StrEnum):
    """Alpha Bidet command set groupings."""

    JX2 = "jx2"


class AlphaBidetModel(StrEnum):
    """Alpha Bidet washlet models."""

    # JX2 command set; the EW/EB/RW/RB suffixes are seat shape and color only.
    JX2 = "JX2"


MODEL_TO_COMMAND_SET: dict[AlphaBidetModel, AlphaBidetCommandSet] = {
    AlphaBidetModel.JX2: AlphaBidetCommandSet.JX2,
}

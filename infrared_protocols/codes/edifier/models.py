"""Edifier speaker models, command-set groupings, and their mapping."""

from enum import StrEnum


class EdifierCommandSet(StrEnum):
    """Edifier command set groupings."""

    R1700BT = "r1700bt"
    R1280DB = "r1280db"
    R1280T = "r1280t"
    S360DB = "s360db"
    RC20G = "rc20g"


class EdifierModel(StrEnum):
    """Edifier speaker models."""

    # R1700BT command set
    R1700BT = "R1700BT"
    R1700BTS = "R1700BTs"
    RC17A = "RC17A"
    RC80B = "RC80B"
    R1855DB = "R1855DB"
    # R1280DB command set
    R1280DB = "R1280DB"
    R2730DB = "R2730DB"
    RC10D1 = "RC10D1"
    R2000DB = "R2000DB"
    # R1280T command set (basic)
    R1280T = "R1280T"
    # S360DB command set
    S360DB = "S360DB"
    RC31A = "RC31A"
    # RC20G command set (unique left/right volume controls)
    RC20G = "RC20G"


MODEL_TO_COMMAND_SET: dict[EdifierModel, EdifierCommandSet] = {
    # R1700BT command set
    EdifierModel.R1700BT: EdifierCommandSet.R1700BT,
    EdifierModel.R1700BTS: EdifierCommandSet.R1700BT,
    EdifierModel.RC17A: EdifierCommandSet.R1700BT,
    EdifierModel.RC80B: EdifierCommandSet.R1700BT,
    EdifierModel.R1855DB: EdifierCommandSet.R1700BT,
    # R1280DB command set
    EdifierModel.R1280DB: EdifierCommandSet.R1280DB,
    EdifierModel.R2730DB: EdifierCommandSet.R1280DB,
    EdifierModel.RC10D1: EdifierCommandSet.R1280DB,
    EdifierModel.R2000DB: EdifierCommandSet.R1280DB,
    # R1280T command set
    EdifierModel.R1280T: EdifierCommandSet.R1280T,
    # S360DB command set
    EdifierModel.S360DB: EdifierCommandSet.S360DB,
    EdifierModel.RC31A: EdifierCommandSet.S360DB,
    # RC20G command set
    EdifierModel.RC20G: EdifierCommandSet.RC20G,
}

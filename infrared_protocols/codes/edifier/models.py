"""Edifier speaker models, command-set groupings, and their mapping.

Mappings can also be found in
https://support.edifier-online.com/hc/en-us/articles/4412111975059-Speaker-Remote-Control-Compatibility-List
"""

from enum import StrEnum, unique


@unique
class EdifierCommandSet(StrEnum):
    """Edifier command set groupings."""

    R1700BT_PRE_2017 = "r1700bt_pre_2017"
    R1700BT_2017 = "r1700bt_2017"
    R1700BTS = "r1700bts"
    R1380DB = "r1380db"
    R1280DB = "r1280db"
    R1280T = "r1280t"
    R2000DB = "r2000db"
    S351DB = "s351db"
    R2730DB = "r2730db"
    S360DB = "s360db"
    RC20G = "rc20g"
    RC2_1B = "rc2_1b"
    RC80B = "rc80b"
    S3000PRO = "s3000pro"
    R2600 = "r2600"


@unique
class EdifierModel(StrEnum):
    """Edifier speaker models."""

    # R1700BT (pre-2017) command set
    R1700BT_PRE_2017 = "R1700BT (pre-2017)"
    RC10B = "RC10B"
    # R1700BT (2017) command set
    R1700BT_2017 = "R1700BT (2017)"
    RC10G = "RC10G"
    # R1700BTs command set
    R1700BTS = "R1700BTs"
    D12 = "D12"
    RC12D = "RC12D"
    RC17A = "RC17A"
    R1855DB = "R1855DB"
    # R1380DB command set
    R1380DB = "R1380DB"
    RC13D = "RC13D"
    # R1280DB command set
    R1280DB = "R1280DB"
    RC10E = "RC10E"
    # R1280T command set (basic)
    R1280T = "R1280T"
    R1600TIII = "R1600TIII"
    R1800TIII = "R1800TIII"
    RC10 = "RC10"
    # R2000DB command set (RC10D remote)
    R2000DB = "R2000DB"
    RC10D = "RC10D"
    # S351DB command set (RCA10C remote)
    S351DB = "S351DB"
    RCA10C = "RCA10C"
    # R2730DB command set (RC10D1 remote)
    R2730DB = "R2730DB"
    RC10D1 = "RC10D1"
    # S360DB command set
    S360DB = "S360DB"
    S350DB = "S350DB"
    RC600A = "RC600A"
    # RC20G command set (unique left/right volume controls)
    RC20G = "RC20G"
    R1850DB = "R1850DB"
    # RC2.1B command set
    S530D = "S530D"
    S730 = "S730"
    # RC80B command set (toggle input buttons)
    RC80B = "RC80B"
    # S3000 Pro command set (RCA10B remote)
    S3000PRO = "S3000 Pro"
    RCA10B = "RCA10B"
    # R2600 command set (RC31A remote)
    R2600 = "R2600"
    RC31A = "RC31A"


MODEL_TO_COMMAND_SET: dict[EdifierModel, EdifierCommandSet] = {
    # R1700BT (pre-2017) command set
    EdifierModel.R1700BT_PRE_2017: EdifierCommandSet.R1700BT_PRE_2017,
    EdifierModel.RC10B: EdifierCommandSet.R1700BT_PRE_2017,
    # R1700BT (2017) command set
    EdifierModel.R1700BT_2017: EdifierCommandSet.R1700BT_2017,
    EdifierModel.RC10G: EdifierCommandSet.R1700BT_2017,
    # R1700BTs command set
    EdifierModel.R1700BTS: EdifierCommandSet.R1700BTS,
    EdifierModel.RC17A: EdifierCommandSet.R1700BTS,
    EdifierModel.R1855DB: EdifierCommandSet.R1700BTS,
    EdifierModel.D12: EdifierCommandSet.R1700BTS,
    EdifierModel.RC12D: EdifierCommandSet.R1700BTS,
    # R1280DB command set
    EdifierModel.R1280DB: EdifierCommandSet.R1280DB,
    EdifierModel.RC10E: EdifierCommandSet.R1280DB,
    # R1280T command set
    EdifierModel.R1280T: EdifierCommandSet.R1280T,
    EdifierModel.R1600TIII: EdifierCommandSet.R1280T,
    EdifierModel.R1800TIII: EdifierCommandSet.R1280T,
    EdifierModel.RC10: EdifierCommandSet.R1280T,
    # R1380DB command set
    EdifierModel.R1380DB: EdifierCommandSet.R1380DB,
    EdifierModel.RC13D: EdifierCommandSet.R1380DB,
    # R2000DB command set
    EdifierModel.R2000DB: EdifierCommandSet.R2000DB,
    EdifierModel.RC10D: EdifierCommandSet.R2000DB,
    # S351DB command set
    EdifierModel.S351DB: EdifierCommandSet.S351DB,
    EdifierModel.RCA10C: EdifierCommandSet.S351DB,
    # R2730DB command set
    EdifierModel.R2730DB: EdifierCommandSet.R2730DB,
    EdifierModel.RC10D1: EdifierCommandSet.R2730DB,
    # S360DB command set
    EdifierModel.S360DB: EdifierCommandSet.S360DB,
    EdifierModel.S350DB: EdifierCommandSet.S360DB,
    EdifierModel.RC600A: EdifierCommandSet.S360DB,
    # RC20G command set
    EdifierModel.RC20G: EdifierCommandSet.RC20G,
    EdifierModel.R1850DB: EdifierCommandSet.RC20G,
    # RC2.1B command set
    EdifierModel.S530D: EdifierCommandSet.RC2_1B,
    EdifierModel.S730: EdifierCommandSet.RC2_1B,
    # RC80B command set
    EdifierModel.RC80B: EdifierCommandSet.RC80B,
    # S3000 Pro command set
    EdifierModel.S3000PRO: EdifierCommandSet.S3000PRO,
    EdifierModel.RCA10B: EdifierCommandSet.S3000PRO,
    # R2600 command set
    EdifierModel.R2600: EdifierCommandSet.R2600,
    EdifierModel.RC31A: EdifierCommandSet.R2600,
}

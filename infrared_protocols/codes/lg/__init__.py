"""LG IR command codes."""

from .tv import LGTVCode
from .tv import make_command as make_tv_command

__all__ = [
    "LGTVCode",
    "make_tv_command",
]

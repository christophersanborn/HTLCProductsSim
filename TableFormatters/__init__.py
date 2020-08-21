# TableFormatters.py
#
# Umbrella for a set of formatter plugins.  Import with:
#
# import formatters/TableFormatters
#
# Usage:
#
# FMT = TableFormatters.GetFMT("fmtid", args)
#

from . import GFM_LogStep
from . import GFM_BollingerTwoSD
from . import GFM_PlainOldList
from . import common as _common

def GetFMT(fmtid, *args, **kwargs):
    FMTclass = _common.get_formatter(fmtid)
    return FMTclass(*args, **kwargs)

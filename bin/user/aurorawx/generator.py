"""CheetahGenerator extension adding SummaryByWeek (Mon-Sun ISO weeks) support.

Selected in skins/aurorawx/skin.conf:

    [Generators]
        generator_list = user.aurorawx.generator.AuroraCheetahGenerator, weewx.reportengine.CopyGenerator

weewx's CheetahGenerator resolves summary generators and filename formats
through the base class attributes (not the instance), so enabling a new
"SummaryBy*" flavour requires registering the week entries on the base
class dictionaries. This module does that at import time; the AuroraWX
subclass is simply the named hook that guarantees the import happens
when the report engine loads the generator list.

The package lives in the WeeWX user directory (bin/user). WeeWX puts bin/
(the parent of the user directory) on sys.path, hence the "user." prefix on
imports.
"""

import datetime
import time

from weeutil.weeutil import TimeSpan
from weewx.cheetahgenerator import CheetahGenerator


def genWeekSpans(start_ts, stop_ts):
    """Generator function that generates start/stop of weeks in an inclusive range.

    Weeks run Monday 00:00 local time through the following Monday 00:00,
    mirroring the semantics of weeutil.weeutil.genDaySpans/genMonthSpans:
    the first span is the week containing start_ts, the last is the week
    containing stop_ts, and a stop_ts that falls exactly on a Monday
    midnight does not produce a final empty week. Week arithmetic uses
    local wall-clock datetimes so spans stay Monday-aligned across
    daylight savings transitions.

    Args:

        start_ts (float): A time stamp somewhere in the first week.
        stop_ts (float): A time stamp somewhere in the last week.

    Yields:
        TimeSpan: A sequence of TimeSpans, where the start is the time stamp
            of the start of the week (Monday 00:00 local) and the stop is
            the time stamp of the start of the next week.
    """
    if None in (start_ts, stop_ts):
        return

    _start_dt = datetime.datetime.fromtimestamp(start_ts)
    _stop_dt = datetime.datetime.fromtimestamp(stop_ts)

    _week = (_start_dt
             - datetime.timedelta(days=_start_dt.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0)
    _stop_week = (_stop_dt
                  - datetime.timedelta(days=_stop_dt.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0)
    if _stop_dt == _stop_week:
        _stop_week -= datetime.timedelta(days=7)

    while _week <= _stop_week:
        _next_week = _week + datetime.timedelta(days=7)
        yield TimeSpan(int(time.mktime(_week.timetuple())),
                       int(time.mktime(_next_week.timetuple())))
        _week = _next_week


class AuroraCheetahGenerator(CheetahGenerator):
    """CheetahGenerator with support for SummaryByWeek sections."""


CheetahGenerator.generator_dict['SummaryByWeek'] = genWeekSpans
CheetahGenerator.format_dict['SummaryByWeek'] = '%Y-%m-%d'

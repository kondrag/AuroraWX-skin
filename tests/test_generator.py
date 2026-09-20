import datetime
import os
import time

import pytest

os.environ["TZ"] = "America/Los_Angeles"
time.tzset()

from weeutil.weeutil import TimeSpan  # noqa: E402
from user.aurorawx.generator import AuroraCheetahGenerator, genWeekSpans  # noqa: E402


def ts(y, mo, d, h=0, mi=0, s=0):
    return time.mktime((y, mo, d, h, mi, s, 0, 0, -1))


def spans(start_ts, stop_ts):
    return list(genWeekSpans(start_ts, stop_ts))


def test_first_span_snaps_to_monday():
    # Wed 2025-09-10 12:00 local -> first span must start Mon 2025-09-08 00:00
    result = spans(ts(2025, 9, 10, 12), ts(2025, 9, 20, 8))
    first = result[0]
    start_dt = datetime.datetime.fromtimestamp(first.start)
    assert (start_dt.weekday(), start_dt.hour, start_dt.minute) == (0, 0, 0)
    assert start_dt.date() == datetime.date(2025, 9, 8)


def test_weeks_run_monday_to_next_monday():
    result = spans(ts(2025, 9, 10, 12), ts(2025, 9, 20, 8))
    assert [datetime.datetime.fromtimestamp(s.start).date() for s in result] == [
        datetime.date(2025, 9, 8),
        datetime.date(2025, 9, 15),
    ]
    assert result[0].stop == result[1].start
    assert result[1].stop > ts(2025, 9, 20, 8)  # last span covers stop_ts


def test_stop_exactly_monday_midnight_excluded():
    # stop_ts is exactly the start of a new week: that empty week must not be emitted
    result = spans(ts(2025, 9, 10, 12), ts(2025, 9, 22, 0))
    last_start = datetime.datetime.fromtimestamp(result[-1].start)
    assert last_start.date() == datetime.date(2025, 9, 15)
    assert result[-1].stop == ts(2025, 9, 22, 0)


def test_start_exactly_monday_midnight_included():
    result = spans(ts(2025, 9, 8, 0), ts(2025, 9, 10, 0))
    assert datetime.datetime.fromtimestamp(result[0].start) == datetime.datetime(2025, 9, 8)


def test_single_partial_week():
    result = spans(ts(2025, 9, 10, 6), ts(2025, 9, 12, 6))
    assert len(result) == 1
    assert isinstance(result[0], TimeSpan)


def test_dst_spring_forward_week_is_23h_short():
    # US DST change 2025-03-09 (02:00 -> 03:00) falls in the Mar 3 week
    result = spans(ts(2025, 3, 4, 12), ts(2025, 3, 13, 12))
    week = result[0]
    assert week.stop - week.start == 7 * 86400 - 3600


def test_dst_fall_back_week_is_1h_long():
    # US DST change 2025-11-02 (02:00 -> 01:00) falls in the Oct 27 week
    result = spans(ts(2025, 10, 29, 12), ts(2025, 11, 5, 12))
    week = result[0]
    assert week.stop - week.start == 7 * 86400 + 3600


def test_none_arguments_yield_nothing():
    assert spans(None, ts(2025, 9, 10)) == []
    assert spans(ts(2025, 9, 10), None) == []


def test_generator_dict_is_patched_for_summary_by_week():
    from weewx.cheetahgenerator import CheetahGenerator

    assert CheetahGenerator.generator_dict["SummaryByWeek"] is genWeekSpans
    assert CheetahGenerator.format_dict["SummaryByWeek"] == "%Y-%m-%d"


def test_subclass_inherits():
    assert issubclass(AuroraCheetahGenerator, __import__(
        "weewx.cheetahgenerator", fromlist=["CheetahGenerator"]).CheetahGenerator)

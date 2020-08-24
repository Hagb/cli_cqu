"""处理时间日期
"""

from datetime import date, datetime, time, timedelta, timezone
from typing import Tuple
from ..data.schedule import Schedule, New2020Schedule
from icalendar import Timezone
import re

__all__ = ("exam_materialize_calendar", "course_materialize_calendar", "VTIMEZONE", "TIMEZONE")

# 14节 表示全天
FULL_DAY = 14

# 北京时间
VTIMEZONE: Timezone = Timezone.from_ical(
    """BEGIN:VTIMEZONE
TZID:Asia/Shanghai
X-LIC-LOCATION:Asia/Shanghai
BEGIN:STANDARD
TZNAME:CST
TZOFFSETFROM:+0800
TZOFFSETTO:+0800
DTSTART:19700101T000000
END:STANDARD
END:VTIMEZONE"""
)
"""默认时区（Asia/Shanghai）的 iCalendar VTIMEZONE"""
TIMEZONE: timezone = VTIMEZONE.to_tz()
"""由 VTIMEZONE 生成的 datetime.timezone 对象，Asia/Shanghai"""

p_day_lesson: re.Pattern = re.compile(r"^(?P<day>[一二三四五六日])\[(?P<lesson>[\d\-]+)节\]$")
re_exam: re.Pattern = re.compile(r'^(\d{4}-\d{2}-\d{2})\(\d+周 星期[一二三四五六日]\)(\d{2}:\d{2})-(\d{2}:\d{2})$')


def exam_materialize_calendar(exam_time: str) -> Tuple[datetime, datetime]:
    time_strs = re_exam.match(exam_time)
    assert isinstance(time_strs, re.Match)
    exam_date: date = date.fromisoformat(time_strs[1])
    return (
        datetime.combine(exam_date, time.fromisoformat(time_strs[2]),
                         TIMEZONE), datetime.combine(exam_date, time.fromisoformat(time_strs[3]), TIMEZONE)
    )


def course_materialize_calendar(t_week: str, t_lesson: str, start: date,
                                schedule: Schedule = New2020Schedule()) -> Tuple[datetime, datetime]:
    """具体化时间日期，将一个 周次+节次 字符串转换成具体的 datetime

    例如

    >>> course_materialize_calendar(t_week="1", t_lesson="一[1-2节]", start=date(2020, 2, 17))
    (datetime(2019, 2, 17, 8, 30), datetime(2017, 2, 17, 10, 10))

    比较特殊的几种编码

    1. `13节`、`14节` 表示全天

    >>> course_materialize_calendar(t_week="1", t_lesson="一[14节]", start=date(2020, 2, 17))
    (datetime(2019, 2, 17, 8, 30), datetime(2017, 2, 17, 23, 59))
    """
    m_day_lesson = p_day_lesson.fullmatch(t_lesson)
    assert isinstance(m_day_lesson, re.Match)
    d_day_lesson: dict = m_day_lesson.groupdict()
    i_week: int = int(t_week)
    i_day: int = DAY_MAP[d_day_lesson["day"]]
    s_lesson: str = d_day_lesson["lesson"]

    partial_days: int = (i_week-1) * 7 + i_day
    if re.match(r"\d+-\d+", s_lesson):
        i_lesson: Tuple[int, int] = tuple([int(i) for i in s_lesson.split("-")])
        partial_times: Tuple[timedelta, timedelta] = (schedule[i_lesson[0]][0], schedule[i_lesson[1]][1])
    elif s_lesson == "14" or s_lesson == "13":
        partial_times = schedule[FULL_DAY]
    else:
        raise ValueError(f"{t_lesson} 无法解析课程节次")

    partial_td: Tuple[timedelta, timedelta] = (
        timedelta(days=partial_days) + partial_times[0], timedelta(days=partial_days) + partial_times[1]
    )
    dt: datetime = datetime.combine(start, time.min, TIMEZONE)
    return (dt + partial_td[0], dt + partial_td[1])


# 星期数的偏移量，以星期一为一周的起始
DAY_MAP = {
    "一": 0,
    "二": 1,
    "三": 2,
    "四": 3,
    "五": 4,
    "六": 5,
    "日": 6,
}

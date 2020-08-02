"""制作日历日程"""
import uuid
from datetime import datetime
from datetime import date
from typing import List
from typing import Tuple
from typing import Union
import re
from icalendar import Calendar
from icalendar import Event
from copy import deepcopy
from ..data.schedule import New2020Schedule
from ..data.schedule import Schedule
from ..model import Course
from ..model import ExperimentCourse
from ..model import Exam
from ..util.datetime import course_materialize_calendar
from ..util.datetime import exam_materialize_calendar

__all__ = ("exams_make_ical", "courses_make_ical")


def exams_make_ical(exams: List[Exam]) -> Calendar:
    cal = Calendar()
    cal.add("prodid", "-//Zombie110year//CLI CQU//")
    cal.add("version", "2.0")
    for exam in exams:
        cal.add_component(exam_build_event(exam))
    return cal

def exam_build_event(exam: Exam) -> Event:
    proto = Event()
    proto.add("summary", f"{exam.identifier}-考试")
    proto.add("location", f"{exam.location}-座位号{exam.seat_no}")
    proto.add("description", f"考试\n学分：{exam.score}" +
              (f"\n类别：{exam.classifier}" if exam.classifier else '') +
              (f"\n考核方式：{exam.exam_type}" if exam.exam_type else '' )
    )

    dt_start, dt_end = exam_materialize_calendar(exam.time)
    proto.add("dtstart", dt_start)
    proto.add("dtend", dt_end)

    # RFC 5545 要求 VEVENT 必须存在 dtstamp 与 uid 属性
    proto.add('dtstamp', datetime.utcnow())
    namespace = uuid.UUID(bytes=
        int(dt_start.timestamp()).to_bytes(length=8, byteorder='big') +
        int(dt_end.timestamp()).to_bytes(length=8, byteorder='big')
    )
    proto.add('uid', uuid.uuid3(namespace, f"{exam.identifier}-考试-{exam.classifier}"))
    return proto

def courses_make_ical(courses: List[Union[Course, ExperimentCourse]],
              start: date,
              schedule: Schedule = New2020Schedule()) -> Calendar:
    cal = Calendar()
    cal.add("prodid", "-//Zombie110year//CLI CQU//")
    cal.add("version", "2.0")
    for course in courses:
        for ev in course_build_event(course, start, schedule):
            cal.add_component(ev)
    return cal


def course_build_event(course: Union[Course, ExperimentCourse], start: date,
                schedule: Schedule) -> List[Event]:
    proto = Event()
    proto.add("summary", course.identifier)
    proto.add("location", course.location)
    if isinstance(course, Course):
        proto.add("description", f"教师：{course.teacher}")
    elif isinstance(course, ExperimentCourse):
        proto.add("description", f"教师：{course.teacher}；值班教师：{course.hosting_teacher}；\n项目：{course.project_name}")
    else:
        raise TypeError(f"{course} 需要是 Course 或 ExperimentCourse，但却是 {type(course)}")

    results = []
    weeks = course.week_schedule.split(",") if "," in course.week_schedule else [course.week_schedule]
    for week in weeks:
        ev: Event = deepcopy(proto)
        t_week = re.match(r"^(\d+)", week)[1]
        t_lesson = course.day_schedule
        first_lesson = course_materialize_calendar(t_week, t_lesson, start, schedule)
        dt_start, dt_end = first_lesson

        ev.add("dtstart", dt_start)
        ev.add("dtend", dt_end)

        # 解析周规则
        if "-" in week:
            a, b = week.split("-")
            count = int(b) - int(a) + 1
        else:
            count = 1
        ev.add("rrule", {"freq": "weekly", "count": count})
        results.append(ev)

        # RFC 5545 要求 VEVENT 必须存在 dtstamp 与 uid 属性
        ev.add('dtstamp', datetime.utcnow())
        namespace = uuid.UUID(bytes=
            int(dt_start.timestamp()).to_bytes(length=8, byteorder='big') +
            int(dt_end.timestamp()).to_bytes(length=8, byteorder='big')
        )
        ev.add('uid', uuid.uuid3(namespace, f"{course.identifier}-{course.teacher}"))
    return results


# depracated
def make_range(string: str) -> List[Tuple[str]]:
    """将 ``1-9``, ``1-4,6-9`` 这样的字符串解析为最小单位（a-b 或 n）序列。
    源字符串中 ``s-e`` 表示一个闭区间

    >>> make_range("1")
    [1]
    >>> make_range("1-9")
    [(1, 9)]
    >>> make_range("1,3-9")
    [1, (3, 9)]
    """
    ans = list()
    for component in string.split(","):
        if re.fullmatch(r"\d+", component):
            ans.append(int(component))
        elif re.fullmatch(r"\d+-\d+", component):
            r = tuple([int(x) for x in component.split("-")])
            ans.append(r)
        else:
            raise ValueError(f"字符串 {string} 格式有问题，{component} 无法解析")
    return ans

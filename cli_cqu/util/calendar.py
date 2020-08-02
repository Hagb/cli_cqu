"""制作日历日程"""
import uuid
from datetime import datetime, date
from typing import List, Union
import re
from icalendar import Calendar, Event
from copy import deepcopy
from ..data.schedule import New2020Schedule, Schedule
from ..model import Course, ExperimentCourse, Exam
from ..util.datetime import course_materialize_calendar, exam_materialize_calendar

__all__ = ("exams_make_ical", "courses_make_ical")


def exams_make_ical(exams: List[Exam]) -> Calendar:
    """生成考试安排的 Calendar 对象

    :param list exams: 考试安排
    """
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
    proto.add(
        "description", f"考试\n学分：{exam.score}" + (f"\n类别：{exam.classifier}" if exam.classifier else '') +
        (f"\n考核方式：{exam.exam_type}" if exam.exam_type else '')
    )

    dt_start, dt_end = exam_materialize_calendar(exam.time)
    proto.add("dtstart", dt_start)
    proto.add("dtend", dt_end)

    # RFC 5545 要求 VEVENT 必须存在 dtstamp 与 uid 属性
    proto.add('dtstamp', datetime.utcnow())
    namespace = uuid.UUID(
        bytes=int(dt_start.timestamp()).to_bytes(length=8, byteorder='big') +
        int(dt_end.timestamp()).to_bytes(length=8, byteorder='big')
    )
    proto.add('uid', uuid.uuid3(namespace, f"{exam.identifier}-考试-{exam.classifier}"))
    return proto


def courses_make_ical(
    courses: List[Union[Course, ExperimentCourse]], start: date, schedule: Schedule = New2020Schedule()
) -> Calendar:
    """生成课程表的 Calendar 对象

    :param list courses: 课程表
    :param date start: 学期的第一天，如 date(2020,8,31)
    :parm Schedule schedule: (可选) 将节次和时间对应起来的时间表，默认是 2020~2021 学年开始使用的时间表.
                             cli_cqu.data.schedule 中可以找到别的其它时间表
    """
    cal = Calendar()
    cal.add("prodid", "-//Zombie110year//CLI CQU//")
    cal.add("version", "2.0")
    for course in courses:
        for ev in course_build_event(course, start, schedule):
            cal.add_component(ev)
    return cal


def course_build_event(course: Union[Course, ExperimentCourse], start: date, schedule: Schedule) -> List[Event]:
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
        namespace = uuid.UUID(
            bytes=int(dt_start.timestamp()).to_bytes(length=8, byteorder='big') +
            int(dt_end.timestamp()).to_bytes(length=8, byteorder='big')
        )
        ev.add('uid', uuid.uuid3(namespace, f"{course.identifier}-{course.teacher}"))
    return results

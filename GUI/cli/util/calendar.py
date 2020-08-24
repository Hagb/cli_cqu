"""制作日历日程"""
import uuid
from datetime import datetime, date
from typing import List, Union, Callable
import re
from icalendar import Calendar, Event, vDDDTypes
from icalendar.cal import Component
from copy import deepcopy
from ..data.schedule import New2020Schedule, Schedule
from ..model import Course, ExperimentCourse, Exam
from ..util.datetime import course_materialize_calendar, exam_materialize_calendar, VTIMEZONE
from .parse import parseCourseIdentifier

__all__ = ("exams_make_ical", "courses_make_ical", "exam_to_event", "course_to_event")


def add_datetime(component: Component, name: str, time: datetime):
    """一个跳过带时区的时间中 VALUE 属性的 workaround

    某些日历软件无法正常解析同时带 TZID 和 VALUE 属性的时间。
    详见 https://github.com/collective/icalendar/issues/75 。
    """
    vdatetime: vDDDTypes = vDDDTypes(time)
    if 'VALUE' in vdatetime.params and 'TZID' in vdatetime.params:
        vdatetime.params.pop('VALUE')
    component.add(name, vdatetime)


def exam_to_event(exam: Exam) -> Event:
    "exams_make_ical 函数 exam2event 参数的默认函数"
    proto = Event()
    cid, cname = parseCourseIdentifier(exam.identifier)
    proto.add("summary", f"考试：{cname}")
    proto.add("location", f"{exam.location}-座位号{exam.seat_no}")
    proto.add(
        "description", f"考试：\n学分：{exam.score}；\n课程编号：{cid}" + (f"；\n类别：{exam.classifier}" if exam.classifier else '') +
        (f"；\n考核方式：{exam.exam_type}" if exam.exam_type else '')
    )
    return proto


def exams_make_ical(exams: List[Exam], exam2event: Callable[[Exam], Event] = exam_to_event) -> Calendar:
    """生成考试安排的 Calendar 对象

    :param list exams: 考试安排
    :param exam2event: (可选) 接受一个 Exam 对象，返回一个 icalendar.Event 对象的函数，用于将 Exam 对象的信息按特定方式转化成 Event 中的信息。其中不包含 DTSTAMP、DTSTART、DTEND 属性。
    """
    cal = Calendar()
    cal.add("prodid", "-//Zombie110year//CLI CQU//")
    cal.add("version", "2.0")
    cal.add_component(VTIMEZONE)
    for exam in exams:
        cal.add_component(exam_build_event(exam, exam2event=exam2event))
    return cal


def exam_build_event(exam: Exam, exam2event: Callable[[Exam], Event]) -> Event:
    proto: Event = exam2event(exam)
    dt_start, dt_end = exam_materialize_calendar(exam.time)
    add_datetime(proto, "dtstart", dt_start)
    add_datetime(proto, "dtend", dt_end)

    # RFC 5545 要求 VEVENT 必须存在 dtstamp 与 uid 属性
    proto.add('dtstamp', datetime.utcnow())
    namespace = uuid.UUID(
        bytes=int(dt_start.timestamp()).to_bytes(length=8, byteorder='big') +
        int(dt_end.timestamp()).to_bytes(length=8, byteorder='big')
    )
    proto.add('uid', uuid.uuid3(namespace, f"{exam.identifier}-考试-{exam.classifier}"))
    return proto


def course_to_event(course: Union[Course, ExperimentCourse]) -> Event:
    "courses_make_ical 函数 course2event 参数的默认函数"
    proto = Event()
    cid, cname = parseCourseIdentifier(course.identifier)
    proto.add("summary", cname)
    proto.add("location", course.location)
    if isinstance(course, Course):
        proto.add("description", f"教师：{course.teacher}；\n课程编号：{cid}；\n学分：{course.score}")
    elif isinstance(course, ExperimentCourse):
        proto.add("description", f"教师：{course.teacher}；\n值班教师：{course.hosting_teacher}；\n课程编号：{cid}；\n项目：{course.project_name}")
    else:
        raise TypeError(f"{course} 需要是 Course 或 ExperimentCourse，但却是 {type(course)}")
    return proto


def courses_make_ical(
    courses: List[Union[Course, ExperimentCourse]],
    start: date,
    schedule: Schedule = New2020Schedule(),
    course2event: Callable[[Union[Course, ExperimentCourse]], Event] = course_to_event
) -> Calendar:
    """生成课程表的 Calendar 对象

    :param list courses: 课程表
    :param date start: 学期的第一天，如 date(2020,8,31)
    :parm Schedule schedule: (可选) 将节次和时间对应起来的时间表，默认是 2020~2021 学年开始使用的时间表.
                             cli_cqu.data.schedule 中可以找到别的其它时间表
    :param courses2event: (可选) 接受一个 Course 或 ExperimentCourse 对象，返回一个 icalendar.Event 对象的函数，用于将 Exam 对象的信息按特定方式转化成 Event 中的信息。其中不包含 DTSTAMP、DTSTART、DTEND 属性。
    """
    cal = Calendar()
    cal.add("prodid", "-//Zombie110year//CLI CQU//")
    cal.add("version", "2.0")
    cal.add_component(VTIMEZONE)
    for course in courses:
        for ev in course_build_event(course, start, schedule, course2event=course2event):
            cal.add_component(ev)
    return cal


def course_build_event(
    course: Union[Course, ExperimentCourse], start: date, schedule: Schedule,
    course2event: Callable[[Union[Course, ExperimentCourse]], Event]
) -> List[Event]:
    proto: Event = course2event(course)
    results = []
    weeks = course.week_schedule.split(",") if "," in course.week_schedule else [course.week_schedule]
    for week in weeks:
        ev: Event = deepcopy(proto)
        t_week = re.match(r"^(\d+)", week)[1]
        t_lesson = course.day_schedule
        first_lesson = course_materialize_calendar(t_week, t_lesson, start, schedule)
        dt_start, dt_end = first_lesson

        add_datetime(ev, "dtstart", dt_start)
        add_datetime(ev, "dtend", dt_end)

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

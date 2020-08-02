"""下载课程表 Demo
"""
from cli_cqu.data.route import Jxgl
from cli_cqu.util.calendar import exams_make_ical, courses_make_ical
import cli_cqu.data.schedule as schedule
import json
from datetime import date

print("这只是个供开发者参考的 demo，日期和时间表都是假设的。")

jxgl = Jxgl(username=input("学号："), password=input("密码："))

# 登陆
try:
    jxgl.login()
except Jxgl.NoUserError:
    print("没有该学号")
    exit(1)
except Jxgl.LoginIncorrectError:
    print("学号或密码错误")
    exit(1)
print("登陆成功！\n")

# 获取学期列表
coursesTerms = jxgl.getCoursesTerms()
print("请从以下学期中选择：\n")
for i in coursesTerms:
    print(f"\t{i}: {coursesTerms[i]}\n")
termId = int(input("输入学期编号："))
courses = jxgl.getCourses(termId)

# 学期的第一天，假设是 2020-08-31
termDate = date(2020, 8, 31)

# 获取课程表的 Calendar 对象，默认使用 2020~2021 学年开始的新时间表
coursesIcal = courses_make_ical(courses, termDate)
# 使用 2020~2021 第一学期前的虎溪时间表：
#cousesIcal = courses_make_ical(courses, termDate, schedule.HuxiSchedule())
# 使用 2020~2021 第一学期前的老校区时间表：
#cousesIcal = courses_make_ical(courses, termDate, schedule.ShaPingBaSchedule())

with open('example.ics', 'wb') as icsFile:
    # ics 文件
    icsFile.write(coursesIcal.to_ical())
with open('example.json', 'wt') as jsonFile:
    # json 文件
    json.dump([i.dict() for i in courses], jsonFile, indent=2, ensure_ascii=False)

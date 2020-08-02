from cli_cqu.data.route import Jxgl
from cli_cqu.util.calendar import exams_make_ical
import json
from datetime import date

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

# 获取考试安排学期列表
# 注：考试安排似乎只会有一个学期…… 所以可以直接 termId = list(examsTerms.keys())[0]
examsTerms = jxgl.getExamsTerms()
print("请从以下学期中选择：\n")
for i in examsTerms:
    print(f"\t{i}: {examsTerms[i]}\n")
termId = int(input("输入学期编号："))
exams = jxgl.getExams(termId)

examsIcal = exams_make_ical(exams)
with open('example.ics', 'wb') as icsFile:
    # ics 文件
    icsFile.write(examsIcal.to_ical())
with open('example.json', 'wt') as jsonFile:
    # json 文件
    json.dump([i.dict() for i in exams], jsonFile, indent=2, ensure_ascii=False)

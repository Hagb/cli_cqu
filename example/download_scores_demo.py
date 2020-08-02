from cli_cqu.data.route import Parsed
import json
try:
    scoresDict = Parsed.Assignment.whole_assignment(input("学号："), input("老教务密码："))
except Parsed.Assignment.LoginIncorrectError:
    print('老教务学号或密码错误')
    exit(1)
with open('example.json', 'wt') as jsonFile:
    # json 文件
    json.dump(scoresDict, jsonFile, indent=2, ensure_ascii=False)

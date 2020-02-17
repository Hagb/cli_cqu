"""CLI CQU 是重庆大学教务系统的命令行界面
"""
import json
import logging
import re
import time
from argparse import ArgumentParser
from getpass import getpass

from bs4 import BeautifulSoup
from requests import Response
from requests import Session

from .data import HOST
from .data.js_equality import chkpwd
from .data.route import Parsed
from .data.ua import UA_IE11
from .excpetion.signal import *

__version__ = '0.1.0'

__all__ = ("App")


class App:
    def __init__(self, username: str = None, password: str = None):
        self.username = username if username is not None else input(
            "username> ")
        self.password = password if password is not None else getpass(
            "password> ").rstrip('\n')
        self.session = Session()
        self.session.headers.update({
            'host': HOST.DOMAIN,
            'connection': "keep-alive",
            'cache-control': "max-age=0",
            'upgrade-insecure-requests': "1",
            'user-agent': UA_IE11,
            'accept':
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
            'referer': HOST.PREFIX,
            'accept-encoding': "gzip, deflate",
            'accept-language': "zh-CN,zh;q=0.9",
        })
        self.__login()

    def mainloop(self, one_cmd: str = None):
        """命令行界面，解析指令执行对应功能"""
        def again(one_cmd: str = None) -> str:
            if one_cmd:
                yield one_cmd
            else:
                while True:
                    yield input("cli cqu> ").strip()

        again = again(one_cmd)

        for cmd in again:
            try:
                self.__run_cmd(cmd)
            except SigHelp as signal:
                show_help()
                print(signal.args[0])
            except SigContinue:
                continue
            except SigExit:
                print("=== Bye ===")
                return
            except Signal as err:
                print(f"!!! 未处理的信号 {err}，由 {cmd} 产生 !!!")

    def __run_cmd(self, cmd: str):
        """执行指令，返回控制信号

        :raises Signal: 各种信号
        """
        if cmd == "":
            raise SigContinue("空指令")
        elif cmd == "exit":
            raise SigExit("主动退出")
        elif cmd == "?" or cmd == "h" or cmd == "help":
            show_help()
        elif cmd == "courses-json":
            self.courses_json()
        else:
            raise SigHelp(f"!!! 未处理的命令： {cmd} !!!")
        raise SigDone

    def __login(self):
        "向主页发出请求，发送帐号密码表单，获取 cookie"
        # 初始化 Cookie
        url = f"{HOST.PREFIX}/home.aspx"
        resp = self.session.get(url)
        # fix: 偶尔不需要设置 cookie, 直接就进入主页了
        # 这是跳转页 JavaScript 的等效代码
        pattern = re.compile(
            r"(?<=document.cookie=')DSafeId=([A-Z0-9]+);(?=';)")
        if pattern.search(resp.text):
            first_cookie = re.search(pattern, resp.text)[1]
            self.session.cookies.set("DSafeId", first_cookie)
            time.sleep(0.680)
            resp = self.session.get(url)
            new_cookie = resp.headers.get("set-cookie",
                                          self.session.cookies.get_dict())
            c = {
                1:
                re.search("(?<=ASP.NET_SessionId=)([a-zA-Z0-9]+)(?=;)",
                          new_cookie)[1],
                2:
                re.search("(?<=_D_SID=)([A-Z0-9]+)(?=;)", new_cookie)[1]
            }
            self.session.cookies.set("ASP.NET_SessionId", c[1])
            self.session.cookies.set("_D_SID", c[2])

        # 发送表单
        url = f"{HOST.PREFIX}/_data/index_login.aspx"
        html = BeautifulSoup(self.session.get(url).text, "lxml")
        login_form = {
            "__VIEWSTATE":
            html.select_one("#Logon > input[name=__VIEWSTATE]")["value"],
            "__VIEWSTATEGENERATOR":
            html.select_one("#Logon > input[name=__VIEWSTATEGENERATOR]")
            ["value"],
            "Sel_Type":
            "STU",
            "txt_dsdsdsdjkjkjc":
            self.username,  # 学号
            "txt_dsdfdfgfouyy":
            "",  # 密码, 实际上的密码加密后赋值给 efdfdfuuyyuuckjg
            "txt_ysdsdsdskgf":
            "",
            "pcInfo":
            "",
            "typeName":
            "",
            "aerererdsdxcxdfgfg":
            "",
            "efdfdfuuyyuuckjg":
            chkpwd(self.username, self.password),
        }
        self.session.post(url, data=login_form)

    def courses_json(self):
        """选择课程表，下载为 JSON 文件"""
        print("=== 下载课程表，保存为 JSON ===")
        filename = input("文件名（可忽略 json 后缀）> ").strip()
        if not filename.endswith(".json"):
            filename = f"{filename}.json"

        info = Parsed.TeachingArrangement.personal_courses(self.session)
        print("=== 选择学年学期 ===")
        xnxq_list = info["Sel_XNXQ"]
        for i, li in enumerate(xnxq_list):
            print(f"{i}: {li['text']}")
        xnxq_i = int(input("学年学期[0|1]> ").rstrip())
        xnxq = info["Sel_XNXQ"][xnxq_i]["value"]

        param = {"Sel_XNXQ": xnxq, "px": 0, "rad": "on"}
        table = Parsed.TeachingArrangement.personal_courses_table(
            self.session, param)
        with open(filename, "wt", encoding="utf-8") as out:
            json.dump([i.dict() for i in table],
                      out,
                      indent=2,
                      ensure_ascii=False)


def show_help():
    print("=== help ===")
    print("""在 `cli cqu>` 提示符后输入指令

    目前提供以下指令：
    * courses-json * 获取 JSON 格式的课程表
    * help | h | ? * 获取帮助信息
    * exit * 退出程序
    """)


def welcome():
    print("=== welcome ===")
    print("""欢迎使用 CLI CQU，你可以输入 help 查看帮助""")


def cli_main():
    parser = ArgumentParser("cli-cqu", description="CQU 教学管理系统的命令行界面")
    parser.add_argument("-u", "--username", help="输入用户名", default=None)
    parser.add_argument("-p", "--password", help="输入密码", default=None)
    parser.add_argument("cmd", help="要执行的指令", nargs="?", default=None)
    args = parser.parse_args()
    app = App(args.username, args.password)
    if not (args.username is not None and args.password is not None
            and args.cmd is not None):
        welcome()
    if args.cmd is not None:
        app.mainloop(args.cmd)
    else:
        app.mainloop()

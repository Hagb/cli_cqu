"""jxgl.cqu.edu.cn 网址的路由
"""
import logging
import re
import time
from typing import List, Union, Dict, Optional
from hashlib import md5

from bs4 import BeautifulSoup
from requests import Session

from ..model import Course, ExperimentCourse, Exam
from . import HOST, HEADERS

__all__ = ("Route", "Parsed", "Jxgl")


class Route:
    home = "/home.aspx"
    mainform = "/MAINFRM.aspx"
    logintest = "/sys/Main_banner.aspx"

    class TeachingArrangement:
        "教学安排模块"
        # 个人课表
        personal_courses = "/znpk/Pri_StuSel.aspx"
        # 查询个人课表
        personal_courses_table = "/znpk/Pri_StuSel_rpt.aspx"
        # 考试安排表
        personal_exams = "/kssw/stu_ksap.aspx"
        # 查询考试安排
        personal_exams_table = "/kssw/stu_ksap_rpt.aspx"

    class Assignment:
        """成绩单

        为了避开因未评教而拒绝提供成绩单查询的行为，通过老教务网接口获取数据。
        """
        # 发送 POST 获取会话
        oldjw_login = "http://oldjw.cqu.edu.cn:8088/login.asp"
        # 全部成绩
        whole_assignment = "http://oldjw.cqu.edu.cn:8088/score/sel_score/sum_score_sel.asp"


class Parsed:
    class Assignment:
        class LoginIncorrectError(ValueError):
            pass

        @staticmethod
        def whole_assignment(u: str, p: str, kwargs: dict = {}) -> dict:
            """通过老教务网接口获取成绩单。

            登录密码和新教务网不同，如果没修改过，应为身份证后 6 位。

            :param str u: 学号
            :param str p: 登录密码
            :param dict kwargs: (可选) 连接时传递给 requests 库的额外参数（详见 requests 库中的 request）

            包含字段::

                学号（str）
                姓名（str）
                专业（str）
                GPA（str）
                查询时间（str）
                详细（List[dict]）
                    课程编码（str）
                    课程名称（str）
                    成绩（str）
                    学分（str）
                    选修（str）
                    类别（str）
                    教师（str）
                    考别（str）
                    备注（str）
                    时间（str）
            """
            login_form = {
                # 学号，非统一身份认证号
                "username": u,
                # 老教务网的密码和新教务不同，一般为身份证后 6 位。
                "password": p,
                # 不知道干啥的，好像也没用
                "submit1.x": 20,
                "submit1.y": 22,
                # 院系快速导航
                "select1": "#"
            }
            session = Session()
            resp = session.post(Route.Assignment.oldjw_login, data=login_form, **kwargs)
            resp_text = resp.content.decode("gbk")
            if "你的密码不正确，请到教务处咨询(学生密码错误请向学院教务人员或辅导员查询)!" in resp_text:
                raise Parsed.Assignment.LoginIncorrectError(
                    "学号或密码错误，老教务处的密码默认为身份证后六位，"
                    #
                    "或到教务处咨询(学生密码错误请向学院教务人员或辅导员查询)!"
                )

            assignments = session.get(Route.Assignment.whole_assignment, **kwargs).content.decode("gbk")
            assparse = BeautifulSoup(assignments, "lxml")

            header_text = str(assparse.select_one("td > p:nth-child(2)"))
            header = [t for t in (re.sub(r"</b>|</?p>|\s", "", t) for t in header_text.split("<b>")) if t != ""]

            details = []
            for tr in assparse.select("tr")[3:-1]:
                tds = [re.sub(r"\s", "", td.text) for td in tr.select("td")]
                data = {
                    "课程编码": tds[1],
                    "课程名称": tds[2],
                    "成绩": tds[3],
                    "学分": tds[4],
                    "选修": tds[5],
                    "类别": tds[6],
                    "教师": tds[7],
                    "考别": tds[8],
                    "备注": tds[9],
                    "时间": tds[10],
                }
                details.append(data)

            查询时间 = re.search(r"查询时间：(2\d{3}-\d{1,2}-\d{1,2} \d{1,2}:\d{1,2}:\d{1,2})", assignments)
            table = {
                "学号": header[0][3:],
                "姓名": header[1][3:],
                "专业": header[2][3:],
                "GPA": header[3][4:],
                "查询时间": 查询时间[1] if 查询时间 is not None else "Unknown",
                "详细": details,
            }
            return table


class Jxgl():
    """与教学管理系统交互

    :param str username: 教学管理系统的用户名（学号）
    :param str password: 教学管理系统的密码
    :param str jxglUrl: (可选) 教学管理系统的地址（含协议名及域名，如"http://jxgl.cqu.edu.cn")
    :param Session session: (可选) 自定义 Session 对象
    :param dict headers: (可选) 访问教学管理系统使用的请求头

    创建后不会自动登陆，需要使用 login 方法来登陆
    """
    class NoUserError(ValueError):
        "使用了不存在的用户名的登陆错误时抛出的异常"
        pass

    class LoginIncorrectError(ValueError):
        "用户名或密码不正确的登陆错误时抛出的异常"
        pass

    class LoginExpired(Exception):
        "登陆 cookies 过期或尚未登陆时抛出的异常"
        pass

    jxglUrl: str
    username: str
    password: str
    session: Session

    def login(self, kwargs: dict = {}) -> None:
        """向主页发出请求，发送帐号密码表单，获取 cookie

        :param dict kwargs: (可选) 连接时传递给 requests 库的额外参数（详见 requests 库中的 request）

        帐号或密码错误则抛出异常 NoUserError 或 LoginIncorrectError
        """
        # 初始化 Cookie
        url = f"{self.jxglUrl}/home.aspx"
        resp = self.session.get(url, **kwargs)
        # fix: 偶尔不需要设置 cookie, 直接就进入主页了
        # 这是跳转页 JavaScript 的等效代码
        pattern = re.compile(r"(?<=document.cookie=')DSafeId=([A-Z0-9]+);(?=';)")
        if pattern.search(resp.text):
            first_cookie = re.search(pattern, resp.text)[1]
            self.session.cookies.set("DSafeId", first_cookie)
            time.sleep(0.680)
            resp = self.session.get(url, **kwargs)
            new_cookie = resp.headers.get("set-cookie", self.session.cookies.get_dict())
            c = {
                1: re.search("(?<=ASP.NET_SessionId=)([a-zA-Z0-9]+)(?=;)", new_cookie)[1],
                2: re.search("(?<=_D_SID=)([A-Z0-9]+)(?=;)", new_cookie)[1]
            }
            self.session.cookies.set("ASP.NET_SessionId", c[1])
            self.session.cookies.set("_D_SID", c[2])

        # 发送表单
        url = f"{self.jxglUrl}/_data/index_login.aspx"
        html = BeautifulSoup(self.session.get(url, **kwargs).text, "lxml")
        login_form = {
            "__VIEWSTATE": html.select_one("#Logon > input[name=__VIEWSTATE]")["value"],
            "__VIEWSTATEGENERATOR": html.select_one("#Logon > input[name=__VIEWSTATEGENERATOR]")["value"],
            "Sel_Type": "STU",
            "txt_dsdsdsdjkjkjc": self.username,  # 学号
            "txt_dsdfdfgfouyy": "",  # 密码, 实际上的密码加密后赋值给 efdfdfuuyyuuckjg
            "txt_ysdsdsdskgf": "",
            "pcInfo": "",
            "typeName": "",
            "aerererdsdxcxdfgfg": "",
            "efdfdfuuyyuuckjg": self._chkpwd(self.username, self.password),
        }
        page_text = self.session.post(url, data=login_form, **kwargs).content.decode(encoding='GBK')
        if "正在加载权限数据..." in page_text:
            return
        if "账号或密码不正确！请重新输入。" in page_text:
            raise self.LoginIncorrectError
        if "该账号尚未分配角色!" in page_text:
            raise self.NoUserError
        else:
            raise ValueError("意料之外的登陆返回页面")

    def __init__(
        self,
        username: str,
        password: str,
        jxglUrl: str = HOST.PREFIX,
        session: Optional[Session] = None,
        headers: dict = HEADERS
    ) -> None:
        self.username: str = username
        self.password: str = password
        self.jxglUrl: str = jxglUrl
        self.session: Session = Session() if session is None else session
        self.session.headers.update(HEADERS)

    def getExamsTerms(self, kwargs: dict = {}) -> Dict[int, str]:
        """获取考试安排的学期列表

        :param dict kwargs: (可选) 连接时传递给 requests 库的额外参数（详见 requests 库中的 request）

        返回一个字典，结构：{学期编号(int): 学期名称(str)}
        注：似乎只会有一个学期
        """
        url: str = f"{self.jxglUrl}{Route.TeachingArrangement.personal_exams}"
        return self.parseExamsTerms(self.session.get(url, **kwargs).text)

    @staticmethod
    def parseExamsTerms(htmlText: str) -> Dict[int, str]:
        """解析考试安排学期列表的 html 文本"""
        el_学年学期 = BeautifulSoup(htmlText, "lxml").select("select[name=sel_xnxq] > option")
        return {int(i.attrs["value"]): i.text for i in el_学年学期}

    def getCoursesTerms(self, kwargs: dict = {}) -> Dict[int, str]:
        """获取课程表的学期列表

        :param dict kwargs: (可选) 连接时传递给 requests 库的额外参数（详见 requests 库中的 request）

        返回一个字典，结构：{学期编号(int): 学期名称(str)}
        """
        url: str = f"{self.jxglUrl}{Route.TeachingArrangement.personal_courses}"
        return self.parseCoursesTerms(self.session.get(url, **kwargs).text)

    @staticmethod
    def parseCoursesTerms(htmlText: str) -> Dict[int, str]:
        """解析课程表学期列表的 html 文本"""
        el_学年学期 = BeautifulSoup(htmlText, "lxml").select("select[name=Sel_XNXQ] > option")
        return {int(i.attrs["value"]): i.text for i in el_学年学期}

    def getCourses(self, termId: int, kwargs: dict = {}) -> List[Union[Course, ExperimentCourse]]:
        """获取指定学期的课程表

        :param int termId: 学期编号，包含在 getCoursesTerms 方法的返回值中
        :param dict kwargs: (可选) 连接时传递给 requests 库的额外参数（详见 requests 库中的 request）
        """
        url = f"{self.jxglUrl}{Route.TeachingArrangement.personal_courses_table}"
        resp = self.session.post(url, data={"Sel_XNXQ": termId, "px": 0, "rad": "on"}, **kwargs)
        if ("您正查看的此页已过期" in resp.text):
            raise self.LoginExpired
        return self.parseCourses(resp.text)

    @staticmethod
    def parseCourses(htmlText: str) -> List[Union[Course, ExperimentCourse]]:
        """解析课程表的 html 文本"""
        listing = BeautifulSoup(htmlText, "lxml").select("table > tbody > tr")
        return [Jxgl._makeCourse(i) for i in listing]

    def getExams(self, termId: int, kwargs: dict = {}) -> List[Exam]:
        """获取指定学期的考试安排

        :param int termId: 学期编号，包含在 getExamsTerms 方法的返回值中
        :param dict kwargs: (可选) 连接时传递给 requests 库的额外参数（详见 requests 库中的 request）
        """
        url = f"{self.jxglUrl}{Route.TeachingArrangement.personal_exams_table}"
        resp = self.session.post(url, data={"sel_xnxq": termId}, **kwargs)
        if ("您正查看的此页已过期" in resp.text):
            raise self.LoginExpired
        return self.parseExams(resp.text)

    @staticmethod
    def parseExams(htmlText: str) -> List[Exam]:
        """解析考试安排的 html 文本"""
        listing = BeautifulSoup(htmlText, "lxml").select("table[ID=ID_Table] > tr")
        return [Jxgl._makeExam(i) for i in listing]

    def isLogined(self, kwargs: dict = {}) -> bool:
        """判断是否处于登陆状态

        :param dict kwargs: (可选) 连接时传递给 requests 库的额外参数（详见 requests 库中的 request）

        处于登陆状态则返回 True，否则返回 False
        """
        return self.session.get(f"{self.jxglUrl}{Route.logintest}", allow_redirects=False, **kwargs).status_code == 200

    @staticmethod
    def _makeExam(tr: BeautifulSoup) -> Exam:
        td = tr.select("td")
        return Exam(
            identifier=td[1].text,
            score=float(td[2].text),
            classifier=td[3].text,
            exam_type=td[4].text,
            time=td[5].text,
            location=td[6].text,
            seat_no=int(td[7].text)
        )

    @staticmethod
    def _makeCourse(tr: BeautifulSoup) -> Union[Course, ExperimentCourse]:
        "根据传入的 tr 元素，获取对应的 Course 对象"
        td = tr.select("td")
        # 第一列是序号，忽略
        if len(td) == 13:
            return Course(
                identifier=td[1].text if td[1].text != "" else td[1].attrs.get("hidevalue", ''),
                score=float(td[2].text if td[2].text != "" else td[2].attrs.get("hidevalue", '')),
                time_total=float(td[3].text if td[3].text != "" else td[3].attrs.get("hidevalue", '')),
                time_teach=float(td[4].text if td[4].text != "" else td[4].attrs.get("hidevalue", '')),
                time_practice=float(td[5].text if td[5].text != "" else td[5].attrs.get("hidevalue", '')),
                classifier=td[6].text if td[6].text != "" else td[6].attrs.get("hidevalue", ''),
                teach_type=td[7].text if td[7].text != "" else td[7].attrs.get("hidevalue", ''),
                exam_type=td[8].text if td[8].text != "" else td[8].attrs.get("hidevalue", ''),
                teacher=td[9].text if td[9].text != "" else td[9].attrs.get("hidevalue", ''),
                week_schedule=td[10].text,
                day_schedule=td[11].text,
                location=td[12].text
            )
        elif len(td) == 12:
            return ExperimentCourse(
                identifier=td[1].text if td[1].text != "" else td[1].attrs.get("hidevalue", ''),
                score=float(td[2].text if td[2].text != "" else td[2].attrs.get("hidevalue", '')),
                time_total=float(td[3].text if td[3].text != "" else td[3].attrs.get("hidevalue", '')),
                time_teach=float(td[4].text if td[4].text != "" else td[4].attrs.get("hidevalue", '')),
                time_practice=float(td[5].text if td[5].text != "" else td[5].attrs.get("hidevalue", '')),
                project_name=td[6].text if td[6].text != "" else td[6].attrs.get("hidevalue", ''),
                teacher=td[7].text if td[7].text != "" else td[7].attrs.get("hidevalue", ''),
                hosting_teacher=td[8].text if td[8].text != "" else td[8].attrs.get("hidevalue", ''),
                week_schedule=td[9].text if td[9].text != "" else td[9].attrs.get("hidevalue", ''),
                day_schedule=td[10].text if td[10].text != "" else td[10].attrs.get("hidevalue", ''),
                location=td[11].text if td[11].text != "" else td[11].attrs.get("hidevalue", ''),
            )
        else:
            logging.error("未知的数据结构")
            logging.error(tr.prettify())
            raise ValueError("未知的数据结构")

    @staticmethod
    def _md5(string: str) -> str:
        return md5(string.encode()).hexdigest().upper()

    @staticmethod
    def _chkpwd(username: str, password: str) -> str:
        "赋值给: efdfdfuuyyuuckjg"
        schoolcode = "10611"
        return Jxgl._md5(username + Jxgl._md5(password)[0:30].upper() + schoolcode)[0:30].upper()

import re
from typing import List
__all__ = ("parseCourseIdentifier")


def parseCourseIdentifier(identifier: str) -> List[str]:
    """将教务处原始课程名（如\"[MATH10124]数学分析（2）\"）解析为编号和名称（以上为例，编号为\"MATH10124\"，名称为\"数学分析（2）\"）

    :params str identifier: 原始课程名

    返回一个有两个 str 元素列表，第一个元素为编号，第二个元素为课程名。

    例如

    >>> parseCourseIdentifier(\"[MATH10124]数学分析\")
    [\"MATH10124\", \"数学分析\"]
    """
    matched = re.match(r"\[([^\]]+)\](.*)", identifier)
    if not isinstance(matched, re.Match):
        raise ValueError("原始课程名格式错误")
    return [matched[1], matched[2]]

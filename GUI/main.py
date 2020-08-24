import sys
import os

from PySide2.QtWidgets import QApplication, QMessageBox, QWidget
from PySide2.QtUiTools import QUiLoader
from PySide2.QtCore import QFile

pre_path = os.path.abspath("GUI/")
sys.path.append(pre_path)
# cli_cqu module
from GUI.cli.data import schedule
from GUI.cli.data.route import Jxgl
from GUI.cli.util.calendar import courses_make_ical


class logInDialog:
    def __init__(self):
        # 加载窗体控件UI文件
        qfile_logIn = QFile("ui/loginDialog.ui")
        qfile_logIn.open(QFile.ReadOnly)
        qfile_logIn.close()
        # load window widgets
        self.loginui = QUiLoader().load(qfile_logIn)
        self.loginui.logInButton.clicked.connect(self.handleLogin)
        self.loginui.resetButton.clicked.connect(self.handleReset)

    def handleLogin(self):
        StuNum, PassWord = self.loginui.stuNum.text(), self.loginui.password.text()
        jwcConnection = Jxgl(username=StuNum, password=PassWord, jxglUrl="http://jxgl.cqu.edu.cn/")
        print(StuNum, PassWord)
        print("登录中")
        try:
            jwcConnection.login()
        except Jxgl.NoUserError:
            QMessageBox.critical(self.loginui, "错误", "无该用户！")
        except Jxgl.LoginIncorrectError:
            QMessageBox.critical(self.loginui, "错误", "学号或密码错误!")

    def handleReset(self):
        self.loginui.stuNum.setText("")
        self.loginui.password.setText("")


class MainWindow:
    def __init__(self):
        qfile_mainWindows = QFile("ui/mainWindow.ui")
        qfile_mainWindows.open(QFile.ReadOnly)
        qfile_mainWindows.close()
        # load window widgets
        self.mainWindows = QUiLoader().load(qfile_mainWindows)




def main():
    app = QApplication([])
    logIn_dialog = logInDialog()
    logIn_dialog.loginui.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

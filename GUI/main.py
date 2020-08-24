import sys

from PySide2.QtWidgets import QApplication, QMessageBox, QWidget
from PySide2.QtUiTools import QUiLoader
from PySide2.QtCore import QFile


class logInDialog:
    def __init__(self):
        # 加载窗体控件UI文件
        qfile_logIn = QFile("ui/loginDialog.ui")
        qfile_logIn.open(QFile.ReadOnly)
        qfile_logIn.close()
        # load window widgets
        self.ui = QUiLoader().load(qfile_logIn)

    def getData(self):
        StuNum = stuNum.text()
        PassWord = password.text()
        return StuNum, PassWord


def main():
    app = QApplication([])
    logIn_dialog = logInDialog()
    logIn_dialog.ui.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

import sys
import os

from PySide2.QtWidgets import QApplication, QMessageBox, QWidget, QMainWindow
from PySide2.QtUiTools import QUiLoader
from PySide2.QtCore import QFile, Signal

pre_path = os.path.abspath("GUI/")
sys.path.append(pre_path)
# cli_cqu module
from GUI.cli.data import schedule
from GUI.cli.data.route import Jxgl
from GUI.cli.util.calendar import courses_make_ical
from GUI.loginDilog import logInDialog

qfile_mainWindows = QFile("ui/mainWindow.ui")
qfile_mainWindows.open(QFile.ReadOnly)
qfile_mainWindows.close()
# load window widgets
mainWindows = QUiLoader().load(qfile_mainWindows)

class MainWindow(QMainWindow):
    def __init__(self, parent=None):

        super(MainWindow, self).__init__(parent)


        show_login_dialog_()


def show_login_dialog_():
    ld = logInDialog()
    ld.exec_()
    # if ld.isValid() is True:
    #     pass
    # else:
    #     ld.loginui.show()

import sys

from GUI.loginDilog import logInDialog
from GUI.mainActivity import MainWindow

from PySide2.QtWidgets import QApplication

if __name__ == '__main__':
    app = QApplication([])
    main_window = MainWindow()
    main_window.show()
    # try:
    #     main = MainWindow()
    #     main.show()
    # finally:
    #     sys.exit()

    sys.exit(app.exec_())
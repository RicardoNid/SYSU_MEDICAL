'''这个模板用于使用逻辑类继承ui类，'''

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

#  TODO: ui_class_py改为实际ui类所在module
from ui_class_py import *

class LogicClass(QMainWindow, UiClass):
    '''
    TODO:
        MainWindow: 改为实际逻辑类名
        QMainWindow: 改为实际窗体类型
        UiClass: 改为实际ui类名
    '''
    def __init__(self, parent=None):
        super(LogicClass, self).__init__(parent)
        self.setupUi(self)

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    window = LogicClass()
    window.show()
    sys.exit(app.exec_())
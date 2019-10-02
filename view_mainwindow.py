'''用于快速验证SYSULUNG的UI'''

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

# from dark_orange import *
from ui_MainWindow import *
from canvas import Canvas


class ZoomWidget(QtWidgets.QSpinBox):

    def __init__(self, value=100):
        super(ZoomWidget, self).__init__()
        self.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        self.setRange(10, 1000)
        self.setSuffix(' %')
        self.setValue(value)
        self.setToolTip('Zoom Level')
        self.setStatusTip(self.toolTip())
        self.setAlignment(QtCore.Qt.AlignCenter)

    def minimumSizeHint(self):
        height = super(ZoomWidget, self).minimumSizeHint().height()
        fm = QtGui.QFontMetrics(self.font())
        width = fm.width(str(self.maximum()))
        return QtCore.QSize(width, height)


class LogicClass(QMainWindow, Ui_MainWindow):

    def __init__(self, parent=None):
        super(LogicClass, self).__init__(parent)

        self.setupUi(self)
        self.ui_action_list = [child.objectName() for child in self.children()
                               if
                               isinstance(child, QtWidgets.QAction)]
        self.init_docks()
        print('在ui中注册的Action：')
        for action in self.ui_action_list:
            print(action)

        self.zoomWidget = ZoomWidget()
        self.zoom = QWidgetAction(self)
        self.zoom.setDefaultWidget(self.zoomWidget)
        self.toolBar.insertAction(self.zoom_out_action, self.zoom)

        self.canvas_area = QScrollArea()
        self.canvas_widget = Canvas()
        self.canvas_area.setWidget(self.canvas_widget)
        self.setCentralWidget(self.canvas_area)
        self.coupling_canvas()

        self.resize(1920,1080)
        self.showFullScreen()

    def init_docks(self):
        '''初始化的一部分，执行初始化子窗口并与其耦合的指令，单列一个函数以提升可读性'''
        # 初始化子窗口
        self.series_list_dock.setWidget(QListWidget())
        self.dataset_tree_dock.setWidget(QTreeWidget())
        self.annotation_list_dock.setWidget(QListWidget())
        self.label_edit_dock.setWidget(QListWidget())

        # 增加子窗口显示/隐藏动作
        self.menuView.addAction(self.series_list_dock.toggleViewAction())
        self.menuView.addAction(self.dataset_tree_dock.toggleViewAction())
        self.menuView.addAction(self.annotation_list_dock.toggleViewAction())
        self.menuView.addAction(self.label_edit_dock.toggleViewAction())

    def coupling_canvas(self):
        '''初始化的一部分，执行与canvas组件耦合的指令，单列一个函数以提升可读性'''
        pass

    Qt.MiddleButton



if __name__ == '__main__':
    import sys

    app = QApplication(sys.argv)
    window = LogicClass()
    window.show()
    sys.exit(app.exec_())

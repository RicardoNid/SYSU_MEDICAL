'''用于快速验证SYSULUNG的UI'''

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

# from dark_orange import *
from ui_MainWindow import *
from canvas import Canvas
import utils


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

        self.zoomWidget = ZoomWidget()
        self.zoom_action = QWidgetAction(self)
        self.zoom_action.setDefaultWidget(self.zoomWidget)
        self.toolBar.insertAction(self.zoom_out_action, self.zoom_action)

        print(self.actions())

        self.init_docks()
        self.init_canvas()

        self.resize(1920, 1080)
        self.showMaximized()

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

    def init_canvas(self):
        '''初始化的一部分，执行与canvas组件耦合的指令，单列一个函数以提升可读性'''
        self.canvas_area = QScrollArea()
        self.canvas_widget = Canvas()
        self.canvas_area.setWidget(self.canvas_widget)
        self.setCentralWidget(self.canvas_area)

        # 从主窗口通过action对canvas进行操作
        # 模式切换
        self.edit_mode_action.triggered.connect(self.edit_mode_slot)
        self.create_polygon_action.triggered.connect(self.create_mode_slot)
        self.create_rectangle_action.triggered.connect(self.create_mode_slot)
        self.create_circle_action.triggered.connect(self.create_mode_slot)
        self.create_polyline_action.triggered.connect(self.create_mode_slot)
        self.create_line_action.triggered.connect(self.create_mode_slot)
        self.create_point_action.triggered.connect(self.create_mode_slot)
        # 撤销操作
        self.canvas_undo_action.triggered.connect(self.canvas_undo_slot)
        # 复制选中的标记
        self.copy_selected_annotations_action.triggered.connect(
            self.canvas_widget.copy_selected_annotations)
        # 删除选中的标记
        self.delete_selected_annotataions_action.triggered.connect(
            self.canvas_widget.delete_selected_annotations)
        # 选中所有标记
        self.select_all_annotations_action.triggered.connect(
            self.canvas_widget.select_all_annotations)
        # 分发actions到canvas菜单
        actions = (self.create_polygon_action, self.create_rectangle_action)
        utils.addActions(self.canvas_widget.menu, actions)
        # 接收canvas信号并作出响应
        self.canvas_widget.is_canvas_creating_signal.connect(
            self.is_canvas_creating_signal_slot)

    ################################################################################
    # 下面的方法与canvas进行交互
    # 主窗口与canvas耦合的方式参见init_canvas
    #
    ################################################################################
    def edit_mode_slot(self):
        '''进入编辑模式'''
        # 进入编辑模式前处理创建模式的残余工作
        if self.canvas_widget.is_current_annotation_finalizable():
            self.canvas_widget.finalise_current_annotation()
        else:
            self.canvas_widget.current_annotation = None
            self.canvas_widget.repaint()
        self.canvas_widget.create_mode = False

    def create_mode_slot(self):
        '''进入创建模式，根据不同action进入不同形状类型'''
        # 若当前编辑的创建还没完成，不能切换模式
        if self.canvas_widget.current_annotation:
            return
        # 进入创建模式前处理编辑模式的残余工作
        # TODO 解除所有选中和高亮状态
        self.canvas_widget.create_mode = True
        # 从action名称中获得形状类型
        type = self.sender().objectName().split('_')[1]
        self.canvas_widget.create_type = type

    def canvas_undo_slot(self):
        '''撤销操作，根据具体状态进行不同操作'''
        # 创建模式下
        if self.canvas_widget.create_mode:
            # （上一个）标记创建已经完成，撤销已完成标记的最后一个点
            if not self.canvas_widget.current_annotation:
                self.canvas_widget.undoLastLine()
            # 有标记正在被创建，撤销当前标记的最后一个点
            else:
                self.canvas_widget.undoLastPoint()
        # 编辑模式下
        else:
            self.canvas_widget.restore_annotations()

    def is_canvas_creating_signal_slot(self, creating):
        '''响应canvas当前标记创建开始和结束（而不是创建模式的开启和结束）的信号'''
        # 开始创建
        if creating:
            print('start creating')
            utils.disable_actions([])
        else:
            print('end creating')


if __name__ == '__main__':
    import sys

    app = QApplication(sys.argv)
    window = LogicClass()
    window.show()
    sys.exit(app.exec_())

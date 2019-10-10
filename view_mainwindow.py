'''用于快速验证SYSULUNG的UI'''

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from functools import partial

from ui import Ui_MainWindow
from canvas import Canvas
from widgets import *

import utils

class MainWindow(QMainWindow, Ui_MainWindow):

    # 声明枚举量
    # 当前缩放的方式
    FIT_WINDOW, FIT_WIDTH, MANUAL_ZOOM = 0, 1, 2
    CREATE_MODE, EDIT_MODE = 0, 1

    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        '''
        ui文件内容包括
            1.按键/菜单选项形式的Action的注册
            2.菜单栏，工具栏中Action的分发
            3.子窗口的注册
            4.主窗口的整体布局    
        '''
        self.setupUi(self)
        '''注册和分发WidgetAction'''
        # 注册zoom_action处理canvas以光标所在点为中心的缩放
        self.zoom_widget = ZoomWidget()
        self.zoom_action = QWidgetAction(self)
        self.zoom_action.setObjectName('zoom_action')
        self.zoom_action.setDefaultWidget(self.zoom_widget)
        self.toolBar.insertAction(self.zoom_out_action, self.zoom_action)
        self.zoom_mode = self.FIT_WINDOW
        # 注册wlww_action处理canvas图像的窗位窗宽调整
        self.wlww_widget = WlwwWidget()
        self.wlww_action = QWidgetAction(self)
        self.wlww_action.setObjectName('wlww_action')
        self.wlww_action.setDefaultWidget(self.wlww_widget)
        self.toolBar.addAction(self.wlww_action)

        self.init_dataset_tree_widget()
        self.init_series_list_widget()
        self.init_annotations_list_widget()
        self.init_label_edit_dock()
        self.init_canvas()

        # 设置窗口显示属性
        self.setFocusPolicy(Qt.ClickFocus)
        self.resize(1920, 1080)
        self.showMaximized()
        #  self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)

    def init_dataset_tree_widget(self):
        self.database_widget = DatabaseWidget()
        self.dataset_tree_dock.setWidget(self.database_widget)
        self.menuView.addAction(self.dataset_tree_dock.toggleViewAction())

    def init_series_list_widget(self):
        self.series_list_dock.setWidget(QListWidget())
        self.menuView.addAction(self.series_list_dock.toggleViewAction())

    def init_annotations_list_widget(self):
        '''初始化的一部分，执行初始化标签列表并与其耦合的指令，单列一个函数以提升可读性'''
        self.annotations_list_widget = AnnotationsListWidget()
        self.annotations_list_dock.setWidget(self.annotations_list_widget)
        self.menuView.addAction(self.annotations_list_dock.toggleViewAction())

    def init_label_edit_dock(self):
        self.label_edit_widget = QWidget()
        self.label_edit_dock.setWidget(self.label_edit_widget)
        self.menuView.addAction(self.label_edit_dock.toggleViewAction())

    def init_canvas(self):
        '''初始化的一部分，执行初始化canvas并与其耦合的指令，单列一个函数以提升可读性'''
        self.canvas_area = QScrollArea()
        # TODO: 原理？看了文档还是不懂，需要进行更多研究
        self.canvas_area.setWidgetResizable(True)
        self.scroll_bars = {Qt.Vertical: self.canvas_area.verticalScrollBar(),
                            Qt.Horizontal: self.canvas_area.horizontalScrollBar()}
        self.canvas_widget = Canvas()
        self.canvas_area.setWidget(self.canvas_widget)
        self.setCentralWidget(self.canvas_area)

        # insight: 代码范式：用例的快速实现
        #   1.将用例建模为action，其objectName()以'_action'结尾，在ui中注册action
        #   2.通过self.action(action_name)调用action，链接到实现函数
        #   3.有的action适合用单独的槽函数实现，链接到以self.action_name_slot为名的槽函数
        #   4.有的action适合与其它相近action一起通过相同函数采用不同参数实现，链接到以partial包装的槽函数
        #   5.有的action可以直接使用canvas中的函数（服务）实现，链接到self.canvas_widget的（partial包装的）函数

        # 从主窗口通过action对canvas进行操作
        # 模式和创建类型切换
        # question: 是否能够使用tab切换模式？
        self.toggle_mode_action.triggered.connect(self.toggle_mode_slot)
        self.create_polygon_action.triggered.connect(
            partial(self.set_mode_slot, self.CREATE_MODE, 'polygon'))
        self.create_rectangle_action.triggered.connect(
            partial(self.set_mode_slot, self.CREATE_MODE, 'rectangle'))
        self.create_circle_action.triggered.connect(
            partial(self.set_mode_slot, self.CREATE_MODE, 'circle'))
        self.create_polyline_action.triggered.connect(
            partial(self.set_mode_slot, self.CREATE_MODE, 'polyline'))
        self.action('create_line').triggered.connect(
            partial(self.set_mode_slot, self.CREATE_MODE, 'line'))
        self.action('create_point').triggered.connect(
            partial(self.set_mode_slot, self.CREATE_MODE, 'point'))

        # 缩放
        self.action('zoom_in').triggered.connect(partial(self.adjust_zoom_value, 1.1))
        self.action('zoom_out').triggered.connect(partial(self.adjust_zoom_value, 0.9))
        self.action('fit_window').triggered.connect(self.fit_window_slot)
        self.action('fit_window_width').triggered.connect(self.fit_window_width_slot)

        # 撤销
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
        # 增加点到邻近边
        self.add_point_to_nearest_edge_action.triggered.connect(
            self.canvas_widget.add_point_to_nearest_edge)
        self.action('hide_selected_annotation').triggered.connect(
            partial(self.canvas_widget.set_selected_annotations_visibility, False))
        self.action('toggle_all_annotatons_visibility').triggered.connect(
            self.toggle_all_annotatons_visibility_slot)

        # 分发actions到canvas菜单
        actions = ['hide_selected_annotation', 'add_point_to_nearest_edge']
        self.add_actions(self.canvas_widget.edit_menu, actions)
        actions = ['create_polygon', 'create_rectangle', 'create_circle',
                   'create_polyline', 'create_line', 'create_point']
        self.add_actions(self.canvas_widget.create_menu, actions)

        '''响应canvas信号'''

        self.zoom_widget.valueChanged.connect(self.zoom_action_slot)
        self.wlww_widget.wlww_changed_signal.connect(self.wlww_action_slot)
        self.canvas_widget.zoom_request.connect(self.zoom_requeset_slot)
        self.canvas_widget.scroll_request.connect(self.scroll_request_slot)
        self.canvas_widget.wlww_request.connect(self.wlww_request_slot)

        # 响应状态变化信号
        self.canvas_widget.annotations_changed_signal.connect(self.annotations_list_widget.refresh)

        # 响应功能可用性信号
        self.canvas_widget.has_edge_tobe_added_signal.\
            connect(lambda x: partial(
            utils.toggle_actions, [self.add_point_to_nearest_edge_action])(x))
        self.canvas_widget.is_canvas_creating_signal.\
            connect(lambda x: partial(
            utils.toggle_actions, [self.add_point_to_nearest_edge_action])(x))

    '''下面的方法协助动作分发的结构化'''
    def action(self, action_name: str) -> QAction:
        return self.findChild(QAction, action_name + '_action')

    def add_actions(self, widget, action_names: list):
        '''
        :param widget: 目标对象
        :param action_names: action名称列表
        '''
        for action_name in action_names:
            if action_name is None:
                widget.addSeparator()
            else:
                widget.addAction(self.action(action_name))

    '''下面的方法与canvas进行交互'''
    def scroll_request_slot(self, delta: int, orientation: int):
        '''响应canvas的滚动请求'''
        units = -delta * 0.1
        bar = self.scroll_bars[orientation]
        bar.setValue(bar.value() + bar.singleStep() * units)

    def zoom_requeset_slot(self, delta: int, pos: QPoint):
        '''响应canvas的缩放请求'''
        canvas_width_old = self.canvas_widget.width()
        coeff = 1.1 if delta > 0 else 0.9
        # 按照倍数系数调整缩放值，触发缩放操作调整画布尺寸
        self.adjust_zoom_value(coeff)
        # 在画布上进行的缩放，以光标位置为中心，
        # 调整尺寸之后，还要进行移动，保证光标在画布上的位置不变
        canvas_width_new = self.canvas_widget.width()
        canvas_scale_factor = canvas_width_new / canvas_width_old
        x_shift = round(pos.x() * canvas_scale_factor) - pos.x()
        y_shift = round(pos.y() * canvas_scale_factor) - pos.y()
        self.scroll_bars[Qt.Horizontal].setValue(
            self.scroll_bars[Qt.Horizontal].value() + x_shift)
        self.scroll_bars[Qt.Vertical].setValue(
            self.scroll_bars[Qt.Vertical].value() + y_shift)

    def adjust_zoom_value(self, coeff: float):
        self.set_zoom_value_mannually(self.zoom_widget.value() * coeff)

    def fit_window_slot(self, value):
        if value:
            self.fit_window_width_action.setChecked(False)
            self.zoom_mode = self.FIT_WINDOW
            self.set_zoom_value_to_fit(self.FIT_WINDOW)

    def fit_window_width_slot(self, value):
        if value:
            self.fit_window_action.setChecked(False)
            self.zoom_mode = self.FIT_WIDTH
            self.set_zoom_value_to_fit(self.FIT_WIDTH)

    def set_zoom_value_to_fit(self, zoom_mode: int) -> None:
        '''设置计算出的缩放比例，触发zoom_action'''
        epsilon = 10.0
        w1 = self.canvas_area.width() - epsilon
        h1 = self.canvas_area.height() - epsilon
        scroll_area_ratio = w1 / h1
        w2 = self.canvas_widget.pixmap.width()
        h2 = self.canvas_widget.pixmap.height()
        pixmap_ratio = w2 / h2
        if zoom_mode == self.FIT_WIDTH:
            self.zoom_widget.setValue(w1 / w2 * 100)
        elif zoom_mode == self.FIT_WINDOW:
            if scroll_area_ratio > pixmap_ratio:
                self.zoom_widget.setValue(h1 / h2 * 100)
            else:
                self.zoom_widget.setValue(w1 / w2 * 100)

    def set_zoom_value_mannually(self, value: float) -> None:
        '''设置缩放比例，触发zoom_action'''
        self.fit_window_action.setChecked(False)
        self.fit_window_width_action.setChecked(False)
        self.zoom_widget.setValue(value)
        self.zoom_mode = self.MANUAL_ZOOM

    def zoom_action_slot(self):
        '''缩放比例变化时触发，进行画布尺寸缩放'''
        self.canvas_widget.scale = 0.01 * self.zoom_widget.value()
        self.canvas_widget.adjustSize()
        self.canvas_widget.update()

    def wlww_request_slot(self, wl_delta, ww_delta):
        '''响应canvas的窗位窗宽调整请求'''
        self.wlww_widget.wl_spin.setValue(self.wlww_widget.wl_spin.value() + wl_delta)
        self.wlww_widget.ww_spin.setValue(self.wlww_widget.ww_spin.value() + ww_delta)

    def wlww_action_slot(self):
        '''窗位窗宽数值变化时触发，按照新的窗位窗位窗宽生成图像，重绘画布'''
        # TODO
        pass

    def toggle_mode_slot(self) -> None:
        '''实现模式切换'''
        if not self.canvas_widget.create_mode:
            self.canvas_widget.create_mode = True
        else:
            self.canvas_widget.create_mode = False

    def set_mode_slot(self, mode: int, create_type='polygon') -> None:
        '''实现所有进行模式和类型变更的action'''
        if mode == self.EDIT_MODE:
            self.canvas_widget.create_mode = False
        elif mode == self.CREATE_MODE:
            self.canvas_widget.create_mode = True
            self.canvas_widget.create_type = create_type

    def toggle_all_annotatons_visibility_slot(self) -> None:
        '''显示/隐藏所有标记，具体逻辑是，若有标记被隐藏，显示所有标记，否则，隐藏所有标记'''
        for annotation in self.canvas_widget.annotations:
            if not annotation.is_visable:
                self.canvas_widget.set_all_annotations_visibility(True)
                return
        self.canvas_widget.set_all_annotations_visibility(False)
        return

    def canvas_undo_slot(self):
        '''撤销操作，根据具体状态进行不同操作'''
        # 创建模式下
        if self.canvas_widget.create_mode:
            # （上一个）标记创建已经完成，撤销已完成标记的最后一个点
            if not self.canvas_widget.current_annotation:
                self.canvas_widget.undo_last_line()
            # 有标记正在被创建，撤销当前标记的最后一个点
            else:
                self.canvas_widget.undo_last_point()
        # 编辑模式下
        else:
            self.canvas_widget.restore_annotations()

    #

if __name__ == '__main__':
    import sys

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

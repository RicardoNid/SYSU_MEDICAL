# insight: 代码范式：用例的快速实现
#   1.将用例建模为action，其objectName()以'_action'结尾，在ui中注册action
#   2.通过self.action(action_name)调用action，链接到实现函数
#   3.有的action适合用单独的槽函数实现，链接到以self.action_name_slot为名的槽函数
#   4.有的action适合与其它相近action一起通过相同函数采用不同参数实现，链接到以partial包装的槽函数
#   5.有的action可以直接使用canvas中的函数（服务）实现，链接到self.canvas_widget的（partial包装的）函数

from common_import import *
from functools import partial
import sys

from ui_MainWindow import  Ui_MainWindow
from canvas import Canvas
from datatypes import *
from widgets import *
from utils import *

from typing import *

class MainWindow(QMainWindow, Ui_MainWindow):

    # 声明枚举量
    # 当前缩放的方式
    FIT_WINDOW, FIT_WIDTH, MANUAL_ZOOM = 0, 1, 2
    CREATE_MODE, EDIT_MODE = 0, 1

    DATABASE_PATH = osp.abspath(r'database')

####初始化####
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
        self.raw_image = np.ndarray(0, dtype=int)
        self.current_file = ''
        self.current_file_wl = 0
        self.current_file_ww = 0

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
        self.toolBar.insertAction(self.wlww_reset_action, self.wlww_action)

        self.init_docks()

        self.coupling_mainwindow_actions()
        self.coupling_dataset_tree_widget()
        self.coupling_series_list_widget()
        self.coupling_annotations_list_widget()
        self.coupling_label_edit_widget()
        self.coupling_canvas()

        # 设置窗口显示属性
        self.setFocusPolicy(Qt.ClickFocus)
        self.resize(1920, 1080)
        self.showMaximized()
        #  self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)

    def init_docks(self):
        '''初始化的一部分，执行浮动子窗口和canvas的初始化，单列一个函数以提升可读性'''
        self.database_widget = DatabaseWidget()
        self.dataset_tree_dock.setWidget(self.database_widget)
        self.menuView.addAction(self.dataset_tree_dock.toggleViewAction())

        self.series_list_widget = SeriesListWidget()
        self.series_list_dock.setWidget(self.series_list_widget)
        self.menuView.addAction(self.series_list_dock.toggleViewAction())

        self.annotations_list_widget = AnnotationsListWidget()
        self.annotations_list_dock.setWidget(self.annotations_list_widget)
        self.menuView.addAction(self.annotations_list_dock.toggleViewAction())

        self.label_edit_widget = LabelEditWidget()
        self.label_edit_dock.setWidget(self.label_edit_widget)
        self.menuView.addAction(self.label_edit_dock.toggleViewAction())

        self.canvas_area = QScrollArea()
        # TODO: 原理？看了文档还是不懂，需要进行更多研究
        self.canvas_area.setWidgetResizable(True)
        self.scroll_bars = {Qt.Vertical: self.canvas_area.verticalScrollBar(),
                            Qt.Horizontal: self.canvas_area.horizontalScrollBar()}
        self.canvas_widget = Canvas()
        self.canvas_area.setWidget(self.canvas_widget)
        self.setCentralWidget(self.canvas_area)

    def coupling_mainwindow_actions(self):
        self.save_file_action.triggered.connect(self.save_current_work)
        self.wlww_reset_action.triggered.connect(self.wlww_reset_slot)

    def coupling_dataset_tree_widget(self):
        self.new_database_action.triggered.connect(self.new_database_slot)
        self.open_database_action.triggered.connect(self.open_database_slot)
        self.database_widget.series_selected_signal.connect(self.input_files_slot)

    def coupling_series_list_widget(self):
        '''初始化的一部分，执行与当前文件序列列表耦合的指令，单列一个函数以提升可读性'''
        '''从主窗口通过action对series_list_widget进行操作'''
        self.action('open_dir').triggered.connect(self.open_dir_slot)
        self.action('open_next_image').triggered.connect(
            partial(self.series_list_widget.change_current_item_slot, 1))
        self.action('open_prev_image').triggered.connect(
            partial(self.series_list_widget.change_current_item_slot, -1))
        '''响应series_list_widget信号'''
        self.series_list_widget.currentItemChanged.connect(self.change_current_file_slot)

    def coupling_annotations_list_widget(self):
        '''初始化的一部分，执行与标签列表耦合的指令，单列一个函数以提升可读性'''
        self.annotations_list_widget.itemSelectionChanged.connect(
            self.selected_annotations_changed_slot)

    def coupling_label_edit_widget(self):
        self.label_edit_widget.apply_label_signal.connect(self.apply_label_slot)

    def coupling_canvas(self):
        '''初始化的一部分，执行与canvas耦合的指令，单列一个函数以提升可读性'''

        '''从主窗口通过action对canvas进行操作'''
        # 模式和创建类型切换
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
        # 响应功能请求
        self.zoom_widget.valueChanged.connect(self.zoom_action_slot)
        self.wlww_widget.wlww_changed_signal.connect(self.wlww_action_slot)
        self.canvas_widget.zoom_request.connect(self.zoom_requeset_slot)
        self.canvas_widget.scroll_request.connect(self.scroll_request_slot)
        self.canvas_widget.wlww_request.connect(self.wlww_request_slot)

        # 响应状态变化信号
        self.canvas_widget.annotations_changed_signal.connect(self.annotations_list_widget.refresh)
        self.canvas_widget.annotation_created_signal.connect(self.label_new_annotation_slot)
        self.canvas_widget.selected_annotations_changed_signal.connect(self.selected_annotations_changed_slot)

        # 响应功能可用性信号
        self.canvas_widget.has_edge_tobe_added_signal.\
            connect(lambda x: partial(
            self.toggle_actions, ['add_point_to_nearest_edge'])(x))
        self.canvas_widget.is_canvas_creating_signal.\
            connect(lambda x: partial(
            self.toggle_actions, ['add_point_to_nearest_edge'])(x))
####初始化完成####

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

    def toggle_actions(self, action_names: List[str], value: bool) -> None:
        for action_name in action_names:
            self.action(action_name).setEnabled(value)

    '''下面的方法与canvas进行交互'''
    def change_current_file_slot(self, file_item: QListWidgetItem):
        if file_item:
            self.save_current_work()
            self.current_file = file_item.text()
            self.current_file_wl, self.current_file_ww, dicom_array = get_dicom_info(self.current_file)
            self.raw_image = dicom_array.copy()
            if (self.wlww_widget.wl_spin.value() == 0) and (self.wlww_widget.ww_spin.value() == 0):
                self.wlww_widget.wl_spin.setValue(self.current_file_wl)
                self.wlww_widget.ww_spin.setValue(self.current_file_ww)
            else:
                self.wlww_action_slot()
            annotations_file = self.current_file.replace('.dcm', '.pkl')
            # 读取标签文件
            if osp.exists(annotations_file):
                with open(annotations_file, 'rb') as annotations_pkl:
                    annotations = pickle.load(annotations_pkl)
                self.canvas_widget.load_annotations(annotations)
            # 保存当前文件

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

    def wlww_reset_slot(self):
        print('reset')
        self.wlww_widget.wl_spin.setValue(self.current_file_wl)
        self.wlww_widget.ww_spin.setValue(self.current_file_ww)

    def wlww_request_slot(self, wl_delta, ww_delta):
        '''响应canvas的窗位窗宽调整请求'''
        self.wlww_widget.wl_spin.setValue(self.wlww_widget.wl_spin.value() + wl_delta)
        self.wlww_widget.ww_spin.setValue(self.wlww_widget.ww_spin.value() + ww_delta)

    def wlww_action_slot(self):
        '''窗位窗宽数值变化时触发，按照新的窗位窗位窗宽生成图像，重绘画布'''
        pixmap = dicom_array2pixmap(
            self.wlww_widget.wl_spin.value(), self.wlww_widget.ww_spin.value(), self.raw_image)
        self.canvas_widget.change_pixmap(pixmap)
        self.fit_window_slot(True)

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

    def label_new_annotation_slot(self, new_annotation: Annotation):
        new_annotation.label = LabelEditDialog.get_label()
        print(new_annotation.label.segmentation)

    def selected_annotations_changed_slot(self, selected_annotations=None):
        '''
        响应被选中标记变化信号，包括从canvas上选中和从annotation_list_widget上选中传出的信号
            1.
            2.更改标签编辑窗口内容为最后被选中的标记的标签内容
        '''
        if self.sender() == self.annotations_list_widget:
            selected_annotations = []
            for index in self.annotations_list_widget.selectedIndexes():
                selected_annotations.append(self.canvas_widget.annotations[index.row()])
            self.canvas_widget.select_specific_annotations(selected_annotations)
        elif self.sender() == self.canvas_widget:
            pass

        if selected_annotations:
            self.label_edit_widget.label = selected_annotations[-1].label
            self.label_edit_widget.refresh()
        else:
            self.label_edit_widget.reset()

    '''下面的方法与database_widget进行交互'''
    def new_database_slot(self):
        '''从指定目录新建dicom数据库'''
        database_dir = QFileDialog.getExistingDirectory(self, '选择要扫描的目录')
        if not database_dir:
            return
        database_name, ok = QInputDialog.getText(self, '输入数据库名称', '数据库名称：')
        if ok:
            self.database_widget.new_database(database_dir, database_name)

    def open_database_slot(self):
        '''从指定.xml文件打开dicom数据库'''
        database_path, ok = QFileDialog.getOpenFileName(self, caption='选择要打开的数据库',
                                                       directory=self.DATABASE_PATH,
                                                       filter='数据库文件(*.xml)')
        if ok:
            self.database_widget.open_database(database_path)

    '''下面的方法与series_list_widget进行交互'''
    def open_dir_slot(self):
        '''打开文件夹，将.dcm文件增加到数据库'''
        files_dir = QFileDialog.getExistingDirectory(self, '选择要打开的目录')
        if not files_dir:
            return
        files = get_dicom_files_path_from_dir(files_dir)
        # TODO: 之后修改为可以添加到任意数据库
        self.database_widget.add_to_database(files)

        self.input_files_slot(files)

    def input_files_slot(self, files):
        '''
        响应输入新的文件更新当前文件序列的请求，有以下来源
            1.从数据库窗口获取序列输入
            2.从open_dir/open_file action输入
        '''
        files = sorted(files)
        self.series_list_widget.refresh_files(files)
        self.series_list_widget.change_current_item_slot(-9999)
        if self.toggle_auto_wlww_action.isChecked():
            self.wlww_reset_slot()

    '''下面的方法与label_edit_widget进行交互'''
    def apply_label_slot(self, label: LabelStruct):
        if self.canvas_widget.selected_annotations:
            self.canvas_widget.selected_annotations[-1].label = label
            self.annotations_list_widget.refresh(self.canvas_widget.annotations)

    '''下面的方法实现全局功能'''
    def save_current_work(self):
        '''保存当前图像的所有标记为图像同名文件'''
        if self.current_file:
            with open(self.current_file.replace('.dcm', '.pkl'), 'wb') as annotations_pkl:
                pickle.dump(self.canvas_widget.annotations, annotations_pkl)

    def closeEvent(self, *args, **kwargs):
        '''退出前事件'''
        super().closeEvent(*args, **kwargs)
        self.database_widget.save_item_states()


app = QApplication(sys.argv)
window = MainWindow()
window.show()
sys.exit(app.exec_())


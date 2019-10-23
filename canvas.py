'''实现画布控件，是图像被展示和标记的区域，占据MainWindow的centralwidget'''

from PyQt5 import QtWidgets
from PyQt5 import QtGui
from PyQt5 import QtCore

from datatypes import Annotation
import utils

# - [maybe] Find optimal epsilon value.

CURSOR_DEFAULT = QtCore.Qt.ArrowCursor
CURSOR_POINT = QtCore.Qt.PointingHandCursor
CURSOR_DRAW = QtCore.Qt.CrossCursor
CURSOR_MOVE = QtCore.Qt.ClosedHandCursor
CURSOR_GRAB = QtCore.Qt.OpenHandCursor

# FIXME:
#  1.全选之后删除

class Canvas(QtWidgets.QWidget):
    '''画布控件，实现所有的标记创建，编辑工作，并进行其绘制'''
    # warning: 配置信号，信号需要是类变量，不能是对象变量
    '''操作请求，希望主窗口实现canvas所需要的操作'''
    # 缩放和滚动的请求，请求主窗口在scrollArea上操作
    zoom_request = QtCore.pyqtSignal(int, QtCore.QPoint)
    scroll_request = QtCore.pyqtSignal(int, int)
    # 调整窗位窗宽的请求，请求主窗口重新生成pixmap传入
    wlww_request = QtCore.pyqtSignal(float, float)

    '''数据池变化通知，希望主窗口在关联视图上响应'''
    # 通知有新标记产生
    annotation_created_signal = QtCore.pyqtSignal(Annotation)
    # 通知标记列表因有标记被创建/复制/删除而变化
    annotations_changed_signal = QtCore.pyqtSignal(list)
    # 通知被选中的标记发生变化
    selected_annotations_changed_signal = QtCore.pyqtSignal(list)
    # 通知标记可见性发生变化
    annotations_visibility_changed_signal = QtCore.pyqtSignal()

    '''可用性和状态变化通知，希望主窗口在action可用性上响应'''
    # 通知现在处于标记创建过程中
    is_canvas_creating_signal = QtCore.pyqtSignal(bool)
    # 通知add_point_to_edge的可用性
    has_edge_tobe_added_signal = QtCore.pyqtSignal(bool)

    def __init__(self, *args, **kwargs):
        # 用于判断邻近关系的阈值
        self.epsilon = kwargs.pop('epsilon', 10.0)
        super(Canvas, self).__init__(*args, **kwargs)
        ################################################################################
        # 支持图像存储和显示
        ################################################################################
        self.pixmap = QtGui.QPixmap()
        ################################################################################
        # 支持模式提示图标绘制
        ################################################################################
        self.mode_icon_opacity = 0.0
        self.has_reached_mode_icon_opacity_peak  = False
        self.mode_icon_timer = QtCore.QTimer()
        self.mode_icon_timer.timeout.connect(self.change_mode_icon_opacity)
        self.create_mode_icon = QtGui.QPixmap(r'icons/create_mode.svg')
        self.edit_mode_icon = QtGui.QPixmap(r'icons/edit_mode.svg')
        ################################################################################
        # 支持模式切换
        ################################################################################
        self._create_mode = False
        self._create_type = 'polygon'
        ################################################################################
        # 支持标记创建
        ################################################################################
        # 当前正在被绘制的标记
        self.current_annotation = None
        self.line_color = QtGui.QColor(0, 0, 255)
        self.virtual_annotation = Annotation(line_color=self.line_color)
        ################################################################################
        # 支持标记存储、恢复和显示
        ################################################################################
        # 画布上所有的标记（标记列表）
        self.annotations = []
        # 标记列表的备份
        self.annotataions_backups = []
        ################################################################################
        # 支持标记选择，用in方法查询
        ################################################################################
        self.selected_annotations = []
        ################################################################################
        # 支持标记移动和复制
        ################################################################################
        self.selected_annotations_copy = []
        # 实时记录是否处于标记移动状态
        self.is_moving_annotations = False
        # 记录标记被选择（移动开始）时
        # 光标指向标记boundingbox左上，右下角的矢量，被用于计算移动过程中标记是否出界
        self.offsets_to_bounding_rect = QtCore.QPoint(), QtCore.QPoint()
        ################################################################################
        # 支持顶点选择、移动和增加
        ################################################################################
        self.hShape = None
        self.hVertex = None
        self.hEdge = None
        ################################################################################
        # 支持光标重绘
        ################################################################################
        self._cursor = CURSOR_DEFAULT
        ################################################################################
        # 支持光标追踪
        ################################################################################
        # 在没有按下鼠标时也追踪光标位置，触发mouseMoveEvent
        self.setMouseTracking(True)
        # 上一个被记录的位置，这个位置被用于追踪移动标记时光标的位置
        self.prev_recorded_point = QtCore.QPoint()
        # 当前光标的位置
        self.current_moved_point = QtCore.QPoint()
        self.glo_current_moved_point = QtCore.QPoint()
        # 上一次moveEvent时光标的位置
        self.prev_moved_point = QtCore.QPoint()
        self.glo_prev_moved_point = QtCore.QPoint()
        # 两次moveEvent之间光标的位移量
        # 采用全局位置计算，保证其反映鼠标位移量，而非在画布上位置的位移量
        self.movement_x = 0
        self.movement_y = 0
        ################################################################################
        # 支持缩放
        ################################################################################
        self.scale = 1.0
        self._painter = QtGui.QPainter()
        # 右键菜单
        self.edit_menu = QtWidgets.QMenu()
        self.create_menu = QtWidgets.QMenu()
        # TODO: 处理fill_annotation相关内容
        self._fill_annotation = False
        self.setFocusPolicy(QtCore.Qt.ClickFocus)

    @property
    def fill_annotation(self):
        return self._fill_annotation

    @fill_annotation.setter
    def fill_annotation(self, value):
        self._fill_annotation = value

    ################################################################################
    # 支持模式切换
    ################################################################################
    @property
    def create_mode(self):
        return self._create_mode

    @create_mode.setter
    def create_mode(self, value):
        '''变更模式的工作由setter处理，对调用者隐藏'''
        # 进入创建模式前处理编辑模式的残余工作
        if value:
            if self._create_mode:
                return
            self.unhighlight_all()
            self.deselect_annotations()
        # 进入编辑模式前处理创建模式的残余工作
        else:
            if not self._create_mode:
                return
            if self.is_current_annotation_finalizable():
                self.finalise_current_annotation()
            else:
                self.current_annotation = None
                self.repaint()
        self._create_mode = value
        self.mode_icon_timer.start(25)

    def unhighlight_all(self):
        if self.hShape:
            self.hShape.clear_highlight_vertex()
        self.hVertex = self.hShape = None

    @property
    def create_type(self):
        return self._create_type

    @create_type.setter
    def create_type(self, value):
        if value not in ['polygon', 'rectangle', 'circle',
                         'line', 'point', 'polyline']:
            raise ValueError('Unsupported create_type: %s' % value)
        self._create_type = value

    ################################################################################
    # 支持撤销操作
    ################################################################################
    # 将最近的的10个标记列表（最近的10个标记状态）备份
    def store_annotations(self):
        # print('store annotations')
        annotations_backup = []
        for annotation in self.annotations:
            # insight: 进行备份时要使用copy方法
            annotations_backup.append(annotation.copy())
        if len(self.annotataions_backups) >= 10:
            self.annotataions_backups = self.annotataions_backups[-9:]
        self.annotataions_backups.append(annotations_backup)

    # 当标记备份中的标记列表多于一个，标记状态是可恢复的
    @property
    def is_annotations_restoreable(self):
        if len(self.annotataions_backups) < 2:
            return False
        return True

    # 从标记备份中取出一个标记列表，覆盖当前列表，重绘canvas，完成恢复
    def restore_annotations(self):
        if not self.is_annotations_restoreable:
            return
        self.annotataions_backups.pop()
        annotations_backup = self.annotataions_backups.pop()
        # 恢复标记列表
        self.annotations = annotations_backup
        self.selected_annotations = []
        self.repaint()

    # TODO: last_point, last_line的命名和功能划分令人迷惑，进行优化
    # 撤销最后一个被创建标记的最后一个点
    def undo_last_line(self):
        if len(self.annotations) == 0:
            return
        self.current_annotation = self.annotations.pop()
        self.current_annotation.setOpen()
        if self.create_type in ['polygon', 'polyline']:
            self.virtual_annotation.points = [self.current_annotation[-1],
                                              self.current_annotation[0]]
        elif self.create_type in ['rectangle', 'line', 'circle']:
            self.current_annotation.points = self.current_annotation.points[0:1]
        elif self.create_type == 'point':
            self.current_annotation = None
        self.is_canvas_creating_signal.emit(bool(self.current_annotation))
        self.repaint()

    # 撤销当前被创建标记的最后一个点
    def undo_last_point(self):
        if not self.current_annotation or self.current_annotation.isClosed():
            return
        self.current_annotation.popPoint()
        if len(self.current_annotation) > 0:
            self.virtual_annotation[0] = self.current_annotation[-1]
        else:
            self.current_annotation = None
            self.is_canvas_creating_signal.emit(False)
        self.repaint()

    def undo(self):
        '''根据当前canvas状态决定撤销操作应当如何被理解'''
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

    ################################################################################
    # 进入，离开和焦点事件，只用于支持刷新光标类型
    ################################################################################
    def enterEvent(self, ev):
        self.override_cursor(self._cursor)

    def leaveEvent(self, ev):
        self.restore_cursor()

    ################################################################################
    # 支持刷新光标类型
    ################################################################################
    # 设置光标类型
    def override_cursor(self, cursor):
        self.restore_cursor()
        self._cursor = cursor
        QtWidgets.QApplication.setOverrideCursor(cursor)

    # 加载光标
    def restore_cursor(self):
        QtWidgets.QApplication.restoreOverrideCursor()

    ################################################################################
    # 支持标记创建
    ################################################################################
    # 完成当前标记的创建，不再增加点
    def finalise_current_annotation(self):
        assert self.current_annotation
        self.current_annotation.close()
        self.annotations.append(self.current_annotation)
        self.annotation_created_signal.emit(self.current_annotation)
        self.store_annotations()
        self.current_annotation = None
        self.is_canvas_creating_signal.emit(False)
        self.annotations_changed_signal.emit(self.annotations)
        self.update()

    def is_current_annotation_finalizable(self):
        # 至少要有三个点才能结束手动结束绘制，两点完成的annotation类型会自动结束绘制
        return self.create_mode and self.current_annotation and len(
            self.current_annotation) > 2

    # 判断两点间的距离是否足够接近，被用于判断创建中的光标是否足够接近起始顶点以将其高亮
    # 选择顶点时的接近判断由annotation.get_nearest_vertex实现
    def is_close_enough(self, p1, p2):
        return utils.distance(p1 - p2) < (self.epsilon / self.scale)

    ################################################################################
    # 支持标记编辑
    ################################################################################
    # 移动顶点以改变标记形状
    def move_vertex(self, pos):
        index, annotation = self.hVertex, self.hShape
        point = annotation[index]
        if self.is_out_of_pixmap(pos):
            pos = self.relocate_outer_point_to_border(point, pos)
        annotation.moveVertexBy(index, pos - point)

    # 增加顶点到邻近边以提升标记精度
    def add_point_to_nearest_edge(self):
        if (self.hShape is None and
                self.hEdge is None and
                self.current_moved_point is None):
            return
        annotation = self.hShape
        index = self.hEdge
        point = self.current_moved_point
        annotation.insertPoint(index, point)
        annotation.highlight_vertex(index, annotation.MOVE_VERTEX)
        self.hShape = annotation
        self.hVertex = index
        self.hEdge = None

    ################################################################################
    # 支持标记移动、复制和删除
    ################################################################################
    # 复制选中标记，用于从外部发起标记复制命令
    def copy_selected_annotations(self):
        if self.selected_annotations:
            self.selected_annotations_copy = \
                [selected_annotation.copy() for
                selected_annotation in self.selected_annotations]
            point = self.selected_annotations_copy[0][0]
            offset = QtCore.QPoint(10, 10)
            self.offsets_to_bounding_rect = QtCore.QPoint(), QtCore.QPoint()
            self.prev_recorded_point = point
            # 尝试向来两个不同方向移动副本
            if not self.move_annotations(self.selected_annotations_copy,
                                         point - offset):
                self.move_annotations(self.selected_annotations_copy,
                                      point + offset)
            # 结束副本的移动，完成复制
            self.end_copy_move()
        return self.selected_annotations

    # 移动选中标记，这是一个随着鼠标移动被不断调用的过程，
    # 在这个过程中
    # 不断修改标记内容
    # 不断判断是否出界，是否成功移动并给出反馈
    def move_annotations(self, annotations, pos):
        if self.is_out_of_pixmap(pos):
            return False

        o1 = pos + self.offsets_to_bounding_rect[0]
        if self.is_out_of_pixmap(o1):
            pos -= QtCore.QPoint(min(0, o1.x()), min(0, o1.y()))
        o2 = pos + self.offsets_to_bounding_rect[1]
        if self.is_out_of_pixmap(o2):
            pos += QtCore.QPoint(min(0, self.pixmap.width() - o2.x()),
                                 min(0, self.pixmap.height() - o2.y()))
        dp = pos - self.prev_recorded_point
        if dp:
            for annotation in annotations:
                annotation.moveBy(dp)
            self.prev_recorded_point = pos
            return True
        return False

    # 结束复制-移动
    def end_copy_move(self):
        assert self.selected_annotations and self.selected_annotations_copy
        assert len(self.selected_annotations_copy) == len(
            self.selected_annotations)
        for i, annotation in enumerate(self.selected_annotations_copy):
            self.annotations.append(annotation)
            self.selected_annotations[i] = annotation
        self.store_annotations()
        self.annotations_changed_signal.emit(self.annotations)
        self.selected_annotations_copy = []
        self.repaint()
        self.store_annotations()
        return True

    def delete_selected_annotations(self):
        if self.selected_annotations:
            for annotation in self.selected_annotations:
                self.annotations.remove(annotation)
            self.store_annotations()
            self.selected_annotations = []
            self.annotations_changed_signal.emit(self.annotations)
            self.update()

    # 判断点是否在图像上
    def is_out_of_pixmap(self, p):
        w, h = self.pixmap.width(), self.pixmap.height()
        return not (0 <= p.x() <= w - 1 and 0 <= p.y() <= h - 1)

    ################################################################################
    # 支持标记和顶点选择
    ################################################################################
    # 将所有的标记置于选中状态，用于从外部发起标记选择命令
    def select_all_annotations(self):
        if self.create_mode:
            return
        self.selected_annotations = []
        for annotation in reversed(self.annotations):
            self.selected_annotations.append(annotation)
        self.selected_annotations_changed_signal.emit(self.selected_annotations)
        self.update()

    # 将指定的标记置于选中状态，用于从外部发起标记选择命令
    # 外部传入的标记列表中，标记的先后顺序应当与self.annotations一致
    def select_specific_annotations(self, annotations):
        if self.create_mode:
            return
        self.selected_annotations = []
        for annotation in reversed(annotations):
            self.selected_annotations.append(annotation)
        self.selected_annotations_changed_signal.emit(self.selected_annotations)
        self.update()

    # 如果当前有高亮顶点，选中高亮顶点，并取消对标记的选中

    def select_pointed_vertex_or_annotation(self, point,
                                            multiple_selection_mode):
        # 如果当前有高亮顶点，选中高亮顶点，并取消对标记的选中
        if self.hVertex is not None:
            index, annotation = self.hVertex, self.hShape
            annotation.highlight_vertex(index, annotation.MOVE_VERTEX)
            self.deselect_annotations()
            return
        # 如果没有，将鼠标点击的标记置于选中状态，用于在画布上选择标记
        # 将选择包含光标的，最后被创建的标记，支持单选和复选
        for annotation in reversed(self.annotations):
            if annotation.is_visable and annotation.containsPoint(point):
                # 成功进行选中则重新计算offsets_to_bounding_rect
                self.calculate_offsets_to_bounding_rect(annotation, point)
                if multiple_selection_mode:
                    if annotation not in self.selected_annotations:
                        self.selected_annotations.append(annotation)
                        self.selected_annotations_changed_signal.emit(
                            self.selected_annotations + [annotation])

                else:
                    self.selected_annotations = [annotation]
                    self.selected_annotations_changed_signal.emit(
                        [annotation])
                # 找到满足条件的标记就将其选中并结束，这样最后创建的标记是最优先的，
                # 否则，最先创建的标记是最优先的
                return
        # 如果也没有，鼠标点击了空白处，取消对标记的选中
        self.deselect_annotations()

    # 取消所有选中标记的选中状态
    def deselect_annotations(self):
        if self.selected_annotations:
            self.selected_annotations = []
            self.selected_annotations_changed_signal.emit([])
            self.update()

    ################################################################################
    # 鼠标的移动，按下和松开事件，键盘的按下事件，以及鼠标滚轮事件
    # 它们一方面提供了交互和用例区隔，另一方面也为功能的实现提供了支持，尤其是光标和滚轮变化的追踪
    # 详细的交互和用例区隔方式见logic.py
    ################################################################################
    # 鼠标移动事件
    def mouseMoveEvent(self, ev):
        # 始终追踪光标位置和位移量，并刷新光标类型
        pos = self.transform_pos(ev.localPos())
        self.prev_moved_point = self.current_moved_point
        self.current_moved_point = pos
        glo_pos = ev.globalPos()
        self.glo_prev_moved_point = self.glo_current_moved_point
        self.glo_current_moved_point = glo_pos
        self.movement_x = self.glo_current_moved_point.x() - self.glo_prev_moved_point.x()
        self.movement_y = self.glo_current_moved_point.y() - self.glo_prev_moved_point.y()
        self.restore_cursor()

        # 调整窗位窗宽:不在创建标记过程中时，无论在创建或是编辑模式
        # 可以通过按住滚轮+ctrl+移动来调整窗位窗宽
        mods = ev.modifiers()
        if QtCore.Qt.ControlModifier == int(mods) and \
                QtCore.Qt.MidButton & ev.buttons():
            # 窗位窗宽的变换并不是空间变换，只是用户需要一个快捷方式，才使用鼠标移动来交互
            # 实际使用中，窗位，窗宽的调整分开进行，分别通过上下/左右移动完成
            # 因此在发送位移时，保留主要方向位移，抑制次要方向位移
            if abs(self.movement_y) > abs(self.movement_x):
                self.wlww_request.emit(-self.movement_y, 0)
            else:
                self.wlww_request.emit(0, self.movement_x)
            return
        # 可以通过按住滚轮+移动来移动画布
        if QtCore.Qt.MidButton & ev.buttons():
            self.override_cursor(CURSOR_GRAB)
            self.scroll_request.emit(self.movement_x * 0.5, QtCore.Qt.Horizontal)
            self.scroll_request.emit(self.movement_y * 0.5, QtCore.Qt.Vertical)

        # 创建模式下,鼠标的移动带来显示的刷新
        if self.create_mode:
            self.virtual_annotation.annotation_type = self.create_type
            self.override_cursor(CURSOR_DRAW)
            if self.current_annotation is None:
                return
            color = self.line_color
            # 处理出界点
            if self.is_out_of_pixmap(pos):
                pos = self.relocate_outer_point_to_border(
                    self.current_annotation[-1], pos)
            # 多边形类型下，当光标足够接近起点时，高亮提示
            if self.create_type == 'polygon' and \
                    len(self.current_annotation) > 1 and \
                    self.is_close_enough(pos, self.current_annotation[0]):
                pos = self.current_annotation[0]
                color = self.current_annotation.line_color
                self.override_cursor(CURSOR_POINT)
                self.current_annotation.highlight_vertex(0,
                                                         Annotation.NEAR_VERTEX)
            # 不同类型下，以不同方式刷新virtual_annotation来支持创建过程的显示
            # 具体地说，virtual_annotation在光标所在点还没被添加到标记时暂时充当标记并被显示
            if self.create_type in ['polygon', 'polyline']:
                self.virtual_annotation[0] = self.current_annotation[-1]
                self.virtual_annotation[1] = pos
            elif self.create_type in ['rectangle', 'circle', 'line']:
                self.virtual_annotation.points = [self.current_annotation[0], pos]
            elif self.create_type == 'point':
                self.virtual_annotation.points = [self.current_annotation[0]]
            self.virtual_annotation.line_color = color
            # question: 创建模式下每次mouseMoveEvent都repaint合理吗？
            self.repaint()
            self.current_annotation.clear_highlight_vertex()
            return

        # 编辑模式下
        else:
            # 按住右键移动进行copy-moving
            if QtCore.Qt.RightButton & ev.buttons():
                # 若已经创建副本，移动被选中标记的副本
                if self.selected_annotations_copy and self.prev_recorded_point:
                    self.override_cursor(CURSOR_MOVE)
                    self.move_annotations(self.selected_annotations_copy, pos)
                    self.repaint()
                # 若还没有创建副本，创建被选中标记的副本
                elif self.selected_annotations:
                    self.selected_annotations_copy = \
                        [selected_annotation.copy() for
                         selected_annotation in self.selected_annotations]
                    self.repaint()
                return

            # 按住左键移动进行标记/顶点的移动
            if QtCore.Qt.LeftButton & ev.buttons():
                if self.hVertex is not None:
                    self.move_vertex(pos)
                    self.repaint()
                    self.is_moving_annotations = True
                elif self.selected_annotations and self.prev_recorded_point:
                    self.override_cursor(CURSOR_MOVE)
                    self.move_annotations(self.selected_annotations, pos)
                    self.repaint()
                    self.is_moving_annotations = True
                return
            # 左右键都没被按下，鼠标移动带来高亮状态的变化，具体来说
            # 遍历所有标记，追踪每个标记上离光标最近（且足够近）的顶点和最近（且足够近）的边，
            # 对于每个标记，尝试找到一个足够近的顶点作为高亮顶点，
            # 若没有，若标记包含光标，则选择标记为高亮形状，最近且足够近的边为高亮边（没有足够近的边则为None）
            # 逻辑上，对顶点的高亮优先于形状的高亮，而每一个后被创建的标记的高亮，会覆盖（因此优先于）前一个标记的高亮
            for annotation in reversed(
                    [anno for anno in self.annotations if anno.is_visable]):
                index = annotation.get_nearest_vertex(pos, self.epsilon / self.scale)
                index_edge = annotation.get_nearest_edge(pos, self.epsilon / self.scale)
                # 如果能找到足够近的点，刷新高亮顶点
                if index is not None:
                    if self.hVertex is not None:
                        self.hShape.clear_highlight_vertex()
                    self.hVertex = index
                    self.hShape = annotation
                    self.hEdge = index_edge
                    # 高亮类型是MOVE_VERTEX,高亮类型决定了这个顶点将如何被绘制
                    annotation.highlight_vertex(index, annotation.MOVE_VERTEX)
                    self.override_cursor(CURSOR_POINT)
                    self.update()
                    break
                elif annotation.containsPoint(pos):
                    if self.hVertex is not None:
                        self.hShape.clear_highlight_vertex()
                    self.hVertex = None
                    self.hShape = annotation
                    self.hEdge = index_edge
                    self.override_cursor(CURSOR_GRAB)
                    self.update()
                    break
            # insight: 注意！此处采用了python的for-else结构
            #   在for循环执行的过程中，如果break被执行了，则不会执行else
            #   相反，如果break没被执行，最后else将被执行
            #   continue不会有这种印象，else仍会被执行
            #   这种结构常常用于代替需要一个布尔哨兵变量的for结构
            # 当没有顶点和形状被高亮时，清楚原先高亮形状中的顶点高亮记录，
            # 然后将所有高亮要素取消
            else:
                if self.hShape:
                    self.hShape.clear_highlight_vertex()
                    self.update()
                self.hVertex, self.hShape, self.hEdge = None, None, None
            # 通过光标重绘说明add_point_to_nearest_edge的可用性
            if self.hEdge and not self.hVertex:
                self.override_cursor(CURSOR_DRAW)
            self.has_edge_tobe_added_signal.emit(self.hEdge is not None)

    # 鼠标按下事件
    def mousePressEvent(self, ev):
        pos = self.transform_pos(ev.localPos())
        # 按下左键时
        if ev.button() == QtCore.Qt.LeftButton:
            # 创建模式下，增加点到正在创建的标记，或是创建新标记
            if self.create_mode:
                if self.current_annotation:
                    if self.create_type == 'polygon':
                        self.current_annotation.addPoint(self.virtual_annotation[1])
                        self.virtual_annotation[0] = self.current_annotation[-1]
                        if self.current_annotation.isClosed():
                            self.finalise_current_annotation()
                    elif self.create_type in ['rectangle', 'circle', 'line']:
                        assert len(self.current_annotation.points) == 1
                        self.current_annotation.points = self.virtual_annotation.points
                        self.finalise_current_annotation()
                    elif self.create_type == 'polyline':
                        self.current_annotation.addPoint(self.virtual_annotation[1])
                        self.virtual_annotation[0] = self.current_annotation[-1]
                        if int(ev.modifiers()) == QtCore.Qt.ControlModifier:
                            self.finalise_current_annotation()
                elif not self.is_out_of_pixmap(pos):
                    self.current_annotation = Annotation(
                        annotation_type=self.create_type)
                    self.current_annotation.addPoint(pos)
                    if self.create_type == 'point':
                        self.finalise_current_annotation()
                    else:
                        if self.create_type == 'circle':
                            self.current_annotation.annotation_type = 'circle'
                        self.virtual_annotation.points = [pos, pos]
                        self.is_canvas_creating_signal.emit(True)
                        self.update()
            # 编辑模式下，进行顶点的添加，顶点或标记的选择
            else:
                # 当顶点的添加可用,且顶点的选择不可用时,进行顶点的添加
                if self.hEdge and not self.hVertex:
                    self.add_point_to_nearest_edge()
                    self.repaint()
                    return
                # 否则进行顶点或标记的选择
                group_mode = (int(ev.modifiers()) == QtCore.Qt.ControlModifier)
                self.select_pointed_vertex_or_annotation(pos,
                                                         multiple_selection_mode=group_mode)
                self.prev_recorded_point = pos
                self.repaint()
        # question: 考虑右键选中的利弊
        #   pros: 在进行copy-moving和呼出菜单处理选中标记时不需要先用左键选中，更加连贯
        #   cons: 在想要呼出菜单时只要进行移动就会触发copy-moving，很容易误操作
        #         在多选之后必须按住ctrl才能在保持多选状态的情况下呼出右键菜单，很容易误操作
        #         ！！而且是一个不容易想到的操作，用户很可能以为不能对多选项使用菜单，或是程序有误
        # 按下右键，编辑模式下，进行顶点或标记的选择
        # elif ev.button() == QtCore.Qt.RightButton and not self.create_mode:
        #     group_mode = (int(ev.modifiers()) == QtCore.Qt.ControlModifier)
        #     self.select_pointed_vertex_or_annotation(pos,
        #                                              multiple_selection_mode=group_mode)
        #     self.prev_recorded_point = pos
        #     self.repaint()

    # 鼠标松开事件
    def mouseReleaseEvent(self, ev):
        # 松开右键时
        #   1.如果有选中标记副本，完成复制-移动
        #   2.如果没有，呼出菜单
        if ev.button() == QtCore.Qt.RightButton:
            self.restore_cursor()
            if self.selected_annotations_copy:
                self.end_copy_move()
            else:
                # 创建模式下，仅当前标记创建完成后才呼出菜单
                if self.create_mode and self.current_annotation is None:
                    self.create_menu.exec_(self.mapToGlobal(ev.pos()))
                # 编辑模式下，仅在有高亮标记时才呼出菜单（仅在光标在标记内部时）
                elif not self.create_mode:
                    if not self.hShape:
                        return
                    # 高亮标记已被选中，则不改变选中内容，否则，选中高亮标记
                    if self.hShape in self.selected_annotations:
                        pass
                    else:
                        self.selected_annotations = [self.hShape]
                    self.edit_menu.exec_(self.mapToGlobal(ev.pos()))
        # 松开左键时
        #   1.如果有选中标记，重绘移动光标为抓取光标
        #   2.如果之前正在移动标记，完成移动，进行备份
        elif ev.button() == QtCore.Qt.LeftButton and self.selected_annotations:
            self.override_cursor(CURSOR_GRAB)
            if self.is_moving_annotations:
                self.store_annotations()
                self.is_moving_annotations = False

    # 键盘按下事件
    def keyPressEvent(self, ev):
        key = ev.key()
        # Esc键，取消当前标记的创建
        if key == QtCore.Qt.Key_Escape and self.current_annotation:
            self.current_annotation = None
            self.is_canvas_creating_signal.emit(False)
            self.update()
        # Shift键，完成当前标记的创建
        elif key == QtCore.Qt.Key_Shift and self.is_current_annotation_finalizable():
            self.finalise_current_annotation()

    # 鼠标滚轮事件
    def wheelEvent(self, ev):
        mods = ev.modifiers()
        delta = ev.angleDelta()
        # 按住ctrl时滚动滚轮进行缩放
        if QtCore.Qt.ControlModifier == int(mods):
            self.zoom_request.emit(delta.y(), ev.pos())
            self.adjustSize()
        # 直接滚动滚轮进行移动（只能进行纵向移动）
        else:
            self.scroll_request.emit(delta.x(), QtCore.Qt.Horizontal)
            self.scroll_request.emit(delta.y(), QtCore.Qt.Vertical)
        # warning: 当wheelEvent置accept时，才会被所在控件接收，否则将被发送给父控件
        ev.accept()

    ################################################################################
    # 提供计算支持
    ################################################################################
    # 各种状态下的鼠标移动事件
    # TODO: 对于很多计算方法，没有仔细研究，加入新功能时若遇到问题或是性能瓶颈需要回顾
    # 将坐标由控件坐标系转换到绘图坐标系
    def transform_pos(self, point):
        return point / self.scale - self.caculate_offset_to_center()

    def caculate_offset_to_center(self):
        s = self.scale
        area = super(Canvas, self).size()
        w, h = self.pixmap.width() * s, self.pixmap.height() * s
        aw, ah = area.width(), area.height()
        x = (aw - w) / (2 * s) if aw > w else 0
        y = (ah - h) / (2 * s) if ah > h else 0
        return QtCore.QPoint(x, y)

    # 计算从点指向标记boundingbox左上，右下角的矢量，以QPoint表示
    def calculate_offsets_to_bounding_rect(self, annotation, point):
        rect = annotation.boundingRect()
        x1 = rect.x() - point.x()
        y1 = rect.y() - point.y()
        x2 = (rect.x() + rect.width() - 1) - point.x()
        y2 = (rect.y() + rect.height() - 1) - point.y()
        self.offsets_to_bounding_rect = QtCore.QPoint(x1, y1), QtCore.QPoint(x2, y2)

    # 处理创建标记时出界的点，将它重定位为virtual_annotation和pixmap边界的交点
    def relocate_outer_point_to_border(self, p1, p2):
        size = self.pixmap.size()
        points = [(0, 0),
                  (size.width() - 1, 0),
                  (size.width() - 1, size.height() - 1),
                  (0, size.height() - 1)]
        # x1, y1 should be in the pixmap, x2, y2 should be out of the pixmap
        x1 = min(max(p1.x(), 0), size.width() - 1)
        y1 = min(max(p1.y(), 0), size.height() - 1)
        x2, y2 = p2.x(), p2.y()
        d, i, (x, y) = min(self.intersecting_edges((x1, y1), (x2, y2), points))
        x3, y3 = points[i]
        x4, y4 = points[(i + 1) % 4]
        if (x, y) == (x1, y1):
            # Handle cases where previous point is on one of the edges.
            if x3 == x4:
                return QtCore.QPoint(x3, min(max(0, y2), max(y3, y4)))
            else:  # y3 == y4
                return QtCore.QPoint(min(max(0, x2), max(x3, x4)), y3)
        return QtCore.QPoint(x, y)

    def intersecting_edges(self, point1, point2, points):
        """Find intersecting edges.

        For each edge formed by `points', yield the intersection
        with the line segment `(x1,y1) - (x2,y2)`, if it exists.
        Also return the distance of `(x2,y2)' to the middle of the
        edge along with its index, so that the one closest can be chosen.
        """
        (x1, y1) = point1
        (x2, y2) = point2
        for i in range(4):
            x3, y3 = points[i]
            x4, y4 = points[(i + 1) % 4]
            denom = (y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1)
            nua = (x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)
            nub = (x2 - x1) * (y1 - y3) - (y2 - y1) * (x1 - x3)
            if denom == 0:
                # This covers two cases:
                #   nua == nub == 0: Coincident
                #   otherwise: Parallel
                continue
            ua, ub = nua / denom, nub / denom
            if 0 <= ua <= 1 and 0 <= ub <= 1:
                x = x1 + ua * (x2 - x1)
                y = y1 + ua * (y2 - y1)
                m = QtCore.QPoint((x3 + x4) / 2, (y3 + y4) / 2)
                d = utils.distance(m - QtCore.QPoint(x2, y2))
                yield d, i, (x, y)

    ################################################################################
    # 支持缩放：question 在内部实现缩放？
    ################################################################################
    def sizeHint(self):
        return self.minimumSizeHint()

    def minimumSizeHint(self):
        if self.pixmap:
            return self.scale * self.pixmap.size()
        return super(Canvas, self).minimumSizeHint()

    ################################################################################
    # 支持图像切换，初始化canvas数据池并加载标记文件中的标记列表
    ################################################################################
    #
    def change_pixmap(self, pixmap):
        print('here')
        self.pixmap = pixmap
        self.annotations = []
        self.annotataions_backups = []
        self.selected_annotations = []
        self.hShape = None
        self.hVertex = None
        self.hEdge = None
        self.repaint()

    def load_annotations(self, annotations, replace=True):
        if replace:
            self.annotations = list(annotations)
        else:
            self.annotations.extend(annotations)
        self.store_annotations()
        self.current_annotation = None
        self.repaint()

    ################################################################################
    # 支持canvas中一切的绘制，请仔细了解数据池中各个要素被绘制的逻辑
    ################################################################################
    def paintEvent(self, event):
        if not self.pixmap:
            return super(Canvas, self).paintEvent(event)

        p = self._painter
        p.begin(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.setRenderHint(QtGui.QPainter.HighQualityAntialiasing)
        p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)

        # 坐标系变换
        p.scale(self.scale, self.scale)
        p.translate(self.caculate_offset_to_center())
        # 绘制图像
        p.drawPixmap(0, 0, self.pixmap)

        Annotation.scale = self.scale
        # 标记的绘制
        # 处理绘制完成的标记
        for annotation in self.annotations:
            if annotation.is_visable:
                annotation.fill = (
                                          annotation in self.selected_annotations) or annotation == self.hShape
                annotation.paint(p, selected=(
                        annotation in self.selected_annotations))
        # 处理正在绘制中的标记
        if self.current_annotation:
            self.current_annotation.paint(p)
            self.virtual_annotation.paint(p)
        # 处理复制/移动中的标记
        if self.selected_annotations_copy:
            for selected_annotation_copy in self.selected_annotations_copy:
                selected_annotation_copy.paint(p)

        if (self.fill_annotation and self.create_type == 'polygon' and
                self.current_annotation is not None and len(
                    self.current_annotation.points) >= 2):
            drawing_annotation = self.current_annotation.copy()
            drawing_annotation.addPoint(self.virtual_annotation[1])
            drawing_annotation.fill = True
            drawing_annotation.fill_color.setAlpha(64)
            drawing_annotation.paint(p)

        # 绘制模式提示图标
        if self.mode_icon_opacity >= 0.0:
            p.setOpacity(self.mode_icon_opacity)
            if self.create_mode:
                p.drawPixmap(0, 0, self.create_mode_icon)
            else:
                p.drawPixmap(0, 0, self.edit_mode_icon)

        p.end()

    def change_mode_icon_opacity(self):
        '''模式提示图标绘制，paintEvent的一部分，比较复杂，单列一个函数以提升可读性'''
        if not self.has_reached_mode_icon_opacity_peak:
            self.mode_icon_opacity += 0.1
            if self.mode_icon_opacity >= 1.0:
                self.has_reached_mode_icon_opacity_peak = True
        else:
            self.mode_icon_opacity -= 0.1
            if self.mode_icon_opacity <= 0.0:
                self.has_reached_mode_icon_opacity_peak = False
                self.mode_icon_timer.stop()
        self.repaint()

    ################################################################################
    # 标记可见性修改
    ################################################################################
    def set_selected_annotations_visibility(self, value: bool) -> None:
        '''修改选中标记的可见性'''
        for annotation in self.selected_annotations:
            annotation.is_visable = value
        self.annotations_visibility_changed_signal.emit()
        self.selected_annotations = []
        self.store_annotations()
        self.repaint()

    def set_all_annotations_visibility(self, value: bool) -> None:
        '''修改所有标记的可见性'''
        for annotation in self.annotations:
            annotation.is_visable = value
        self.annotations_visibility_changed_signal.emit()
        self.selected_annotations = []
        self.store_annotations()
        self.repaint()

    def resetState(self):
        self.restore_cursor()
        self.pixmap = None
        self.annotataions_backups = []
        self.update()

if __name__ == '__main__':
    import sys
    from pycallgraph import PyCallGraph
    from pycallgraph.output import GraphvizOutput
    from pycallgraph import Config

    graphviz = GraphvizOutput()
    graphviz.output_file = 'basic.png'
    config = Config()
    print(config)

    with PyCallGraph(output=graphviz, config=config):
        app = QtWidgets.QApplication(sys.argv)
        window = QtWidgets.QMainWindow()
        window.setCentralWidget(Canvas())
        window.showMaximized()
        sys.exit(app.exec_())
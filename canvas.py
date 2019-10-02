'''实现画布控件，是图像被展示和标记的区域，占据MainWindow的centralwidget'''

from PyQt5 import QtWidgets
from PyQt5 import QtGui
from PyQt5 import QtCore

from annotations import Annotation
import utils
import functools

# - [maybe] Find optimal epsilon value.

CURSOR_DEFAULT = QtCore.Qt.ArrowCursor
CURSOR_POINT = QtCore.Qt.PointingHandCursor
CURSOR_DRAW = QtCore.Qt.CrossCursor
CURSOR_MOVE = QtCore.Qt.ClosedHandCursor
CURSOR_GRAB = QtCore.Qt.OpenHandCursor


class Canvas(QtWidgets.QWidget):
    # warning: 配置信号，信号需要是类变量，不能是对象变量

    # 与canvas_area层进行耦合
    zoomRequest = QtCore.pyqtSignal(int, QtCore.QPoint)
    scrollRequest = QtCore.pyqtSignal(int, int)

    wlwwRequest = QtCore.pyqtSignal(float, float)

    newShape = QtCore.pyqtSignal()
    selectionChanged = QtCore.pyqtSignal(list)
    shapeMoved = QtCore.pyqtSignal()
    drawingPolygon = QtCore.pyqtSignal(bool)
    edgeSelected = QtCore.pyqtSignal(bool)

    def __init__(self, *args, **kwargs):
        # 用于判断邻近关系的阈值
        self.epsilon = kwargs.pop('epsilon', 10.0)
        super(Canvas, self).__init__(*args, **kwargs)

        # 数据支持
        # 支持当前交互模式判别
        # 若_create_mode不为True，则为编辑模式
        self._create_mode = True
        self._create_type = 'linestrip'
        # 支持当前绘图设定查询
        self._fill_shape = False

        # 数据变量
        # 标记列表和备份数据
        self.movingShape = False
        # 当前正在绘制的标记
        self.current = None
        # 当前窗口中的所有标记
        self.annotations = []
        self.annotataions_backups = []
        # 当前选中的形状
        self.selected_shapes = []
        # question: 备份？
        self.selected_shapes_copy = []
        self.lineColor = QtGui.QColor(0, 0, 255)
        # 正在绘制的标记的最后一条边，具体如下
        #   - create_type == 'polygon': edge from last point to current
        #   - create_type == 'rectangle': diagonal line of the rectangle
        #   - create_type == 'line': the line
        #   - create_type == 'point': the point
        self.line = Annotation(line_color=self.lineColor)
        self.prevPoint = QtCore.QPoint()
        # TODO: 补充注释
        self.prevMovePoint = QtCore.QPoint()
        self.prevprevMovePoint = None
        self.offsets = QtCore.QPoint(), QtCore.QPoint()
        self.scale = 1.0
        # TODO: 补充注释
        self.visible = {}

        self.pixmap = QtGui.QPixmap()
        self.pixmap = QtGui.QPixmap(
            r'C:\Users\lsfan\PycharmProjects\SYSU_LUNG\EVA.jpg')
        # question: 为何这样设计？
        self._hideBackround = False
        self.hideBackround = False
        # 高亮的shape，顶点和边
        self.hShape = None
        self.hVertex = None
        self.hEdge = None

        self._painter = QtGui.QPainter()
        self._cursor = CURSOR_DEFAULT
        # Menus:
        # 0: right-click without selection and dragging of annotations
        # 1: right-click with selection and dragging of annotations
        self.menus = (QtWidgets.QMenu(), QtWidgets.QMenu())
        # Set widget options.
        self.setMouseTracking(True)
        self.setFocusPolicy(QtCore.Qt.WheelFocus)

        print('init over')

    # ----------property属性----------#
    @property
    def create_mode(self):
        return self._create_mode

    @create_mode.setter
    def create_mode(self, value):
        self._create_mode = value
        # 进入创建模式，将高亮和选中内容清空
        if value:
            self.unHighlight()
            self.deSelectShape()

    '''下面的property属性定义了当前所处模式和模式改变方法'''
    @property
    def create_type(self):
        return self._create_type

    @create_type.setter
    def create_type(self, value):
        if value not in ['polygon', 'rectangle', 'circle',
                         'line', 'point', 'linestrip']:
            raise ValueError('Unsupported create_type: %s' % value)
        self._create_type = value

    @property
    def fill_shape(self):
        return self._fill_shape

    @fill_shape.setter
    def fill_shape(self, value):
        self._fill_shape = value

    '''下面的函数支持标记编辑的撤销'''
    # 将最近的的10个标记列表（最近的10个标记状态）备份
    def store_annotations(self):
        annotations_backup = []
        for annotation in self.annotations:
            annotations_backup.append(annotation.copy())
        if len(self.annotataions_backups) >= 10:
            self.annotataions_backups = self.annotataions_backups[-9:]
        self.annotataions_backups.append(annotations_backup)
    
    # 当标记备份中的标记列表多于一个，标记状态是可恢复的
    @property
    def is_annotation_restoreable(self):
        if len(self.annotataions_backups) < 2:
            return False
        return True

    # 从标记备份中取出一个标记列表，覆盖当前列表，重绘canvas完成恢复
    def restore_annotations(self):
        if not self.is_annotation_restoreable:
            return
        self.annotataions_backups.pop()  # latest
        annotations_backup = self.annotataions_backups.pop()
        self.annotations = annotations_backup
        self.selected_shapes = []
        for annotation in self.annotations:
            annotation.selected = False
        self.repaint()

    '''下面的事件和函数支持光标变化'''
    def enterEvent(self, ev):
        self.override_cursor(self._cursor)

    def leaveEvent(self, ev):
        self.restore_cursor()

    def focusInEvent(self, ev):
        print('focusin')

    def focusOutEvent(self, ev):
        print('focusout')
        self.restore_cursor()

    # 根据传入的光标类型重绘光标
    def override_cursor(self, cursor):
        self.restore_cursor()
        self._cursor = cursor
        QtWidgets.QApplication.setOverrideCursor(cursor)

    # 将光标恢复原始状态
    def restore_cursor(self):
        QtWidgets.QApplication.restoreOverrideCursor()

    '''布尔条件判断'''
    def is_shape_visible(self, shape):
        return self.visible.get(shape, True)

    def is_current_shape_finalizable(self):
        # 至少要有三个点才能结束手动结束绘制，两点完成的shape类型会自动结束绘制
        return self.create_mode and self.current and len(self.current) > 2

    def is_close_enough(self, p1, p2):
        return utils.distance(p1 - p2) < (self.epsilon / self.scale)

    def is_out_of_pixmap(self, p):
        w, h = self.pixmap.width(), self.pixmap.height()
        return not (0 <= p.x() <= w - 1 and 0 <= p.y() <= h - 1)

    # ----------标记绘制和编辑----------#

    def addPointToEdge(self):
        # 需要有一个选中的标记，一条选中的边和一个前置点
        if (self.hShape is None and
                self.hEdge is None and
                self.prevMovePoint is None):
            return
        shape = self.hShape
        index = self.hEdge
        point = self.prevMovePoint
        shape.insertPoint(index, point)
        shape.highlightVertex(index, shape.MOVE_VERTEX)
        self.hShape = shape
        self.hVertex = index
        self.hEdge = None

    def endMove(self, copy):
        assert self.selected_shapes and self.selected_shapes_copy
        assert len(self.selected_shapes_copy) == len(self.selected_shapes)
        # del shape.fill_color
        # del shape.line_color
        if copy:
            for i, shape in enumerate(self.selected_shapes_copy):
                self.annotations.append(shape)
                self.selected_shapes[i].selected = False
                self.selected_shapes[i] = shape
        else:
            for i, shape in enumerate(self.selected_shapes_copy):
                self.selected_shapes[i].points = shape.points
        self.selected_shapes_copy = []
        self.repaint()
        self.store_annotations()
        return True

    def deSelectShape(self):
        if self.selected_shapes:
            self.setHiding(False)
            self.selectionChanged.emit([])
            self.update()

    def deleteSelected(self):
        deleted_shapes = []
        if self.selected_shapes:
            for shape in self.selected_shapes:
                self.annotations.remove(shape)
                deleted_shapes.append(shape)
            self.store_annotations()
            self.selected_shapes = []
            self.update()
        return deleted_shapes

    def copySelectedShapes(self):
        if self.selected_shapes:
            self.selected_shapes_copy = [s.copy() for s in self.selected_shapes]
            self.boundedShiftShapes(self.selected_shapes_copy)
            self.endMove(copy=True)
        return self.selected_shapes

    def finalise(self):
        assert self.current
        self.current.close()
        self.annotations.append(self.current)
        self.store_annotations()
        self.current = None
        self.setHiding(False)
        self.newShape.emit()
        self.update()

    def boundedMoveVertex(self, pos):
        index, shape = self.hVertex, self.hShape
        point = shape[index]
        if self.is_out_of_pixmap(pos):
            pos = self.intersectionPoint(point, pos)
        shape.moveVertexBy(index, pos - point)

    def boundedMoveShapes(self, shapes, pos):
        if self.is_out_of_pixmap(pos):
            return False  # No need to move
        o1 = pos + self.offsets[0]
        if self.is_out_of_pixmap(o1):
            pos -= QtCore.QPoint(min(0, o1.x()), min(0, o1.y()))
        o2 = pos + self.offsets[1]
        if self.is_out_of_pixmap(o2):
            pos += QtCore.QPoint(min(0, self.pixmap.width() - o2.x()),
                                 min(0, self.pixmap.height() - o2.y()))
        # XXX: The next line tracks the new position of the cursor
        # relative to the shape, but also results in making it
        # a bit "shaky" when nearing the border and allows it to
        # go outside of the shape's area for some reason.
        # self.calculateOffsets(self.selected_shapes, pos)
        dp = pos - self.prevPoint
        if dp:
            for shape in shapes:
                shape.moveBy(dp)
            self.prevPoint = pos
            return True
        return False

    def selectShapes(self, shapes):
        self.setHiding()
        self.selectionChanged.emit(shapes)
        self.update()

    def selectShapePoint(self, point, multiple_selection_mode):
        """Select the first shape created which contains this point."""
        if self.hVertex is not None:  # A vertex is marked for selection.
            index, shape = self.hVertex, self.hShape
            shape.highlightVertex(index, shape.MOVE_VERTEX)
        else:
            for shape in reversed(self.annotations):
                if self.is_shape_visible(shape) and shape.containsPoint(point):
                    self.calculateOffsets(shape, point)
                    self.setHiding()
                    if multiple_selection_mode:
                        if shape not in self.selected_shapes:
                            self.selectionChanged.emit(
                                self.selected_shapes + [shape])
                    else:
                        self.selectionChanged.emit([shape])
                    return
        self.deSelectShape()

    def hideBackroundShapes(self, value):
        self.hideBackround = value
        if self.selected_shapes:
            # Only hide other annotations if there is a current selection.
            # Otherwise the user will not be able to select a shape.
            self.setHiding(True)
            self.repaint()

    def setHiding(self, enable=True):
        self._hideBackround = self.hideBackround if enable else False

    # question: what for?
    def boundedShiftShapes(self, shapes):
        # Try to move in one direction, and if it fails in another.
        # Give up if both fail.
        point = shapes[0][0]
        offset = QtCore.QPoint(2.0, 2.0)
        self.offsets = QtCore.QPoint(), QtCore.QPoint()
        self.prevPoint = point
        if not self.boundedMoveShapes(shapes, point - offset):
            self.boundedMoveShapes(shapes, point + offset)

    # ----------快捷计算----------#

    def transformPos(self, point):
        # question: 控件坐标系和painter坐标系有何不同？
        """Convert from widget-logical coordinates to painter-logical ones."""
        return point / self.scale - self.offsetToCenter()

    def offsetToCenter(self):
        s = self.scale
        area = super(Canvas, self).size()
        w, h = self.pixmap.width() * s, self.pixmap.height() * s
        aw, ah = area.width(), area.height()
        x = (aw - w) / (2 * s) if aw > w else 0
        y = (ah - h) / (2 * s) if ah > h else 0
        return QtCore.QPoint(x, y)

    def calculateOffsets(self, shape, point):
        rect = shape.boundingRect()
        x1 = rect.x() - point.x()
        y1 = rect.y() - point.y()
        x2 = (rect.x() + rect.width() - 1) - point.x()
        y2 = (rect.y() + rect.height() - 1) - point.y()
        self.offsets = QtCore.QPoint(x1, y1), QtCore.QPoint(x2, y2)

    def intersectionPoint(self, p1, p2):
        # Cycle through each image edge in clockwise fashion,
        # and find the one intersecting the current line segment.
        # http://paulbourke.net/geometry/lineline2d/
        size = self.pixmap.size()
        points = [(0, 0),
                  (size.width() - 1, 0),
                  (size.width() - 1, size.height() - 1),
                  (0, size.height() - 1)]
        # x1, y1 should be in the pixmap, x2, y2 should be out of the pixmap
        x1 = min(max(p1.x(), 0), size.width() - 1)
        y1 = min(max(p1.y(), 0), size.height() - 1)
        x2, y2 = p2.x(), p2.y()
        d, i, (x, y) = min(self.intersectingEdges((x1, y1), (x2, y2), points))
        x3, y3 = points[i]
        x4, y4 = points[(i + 1) % 4]
        if (x, y) == (x1, y1):
            # Handle cases where previous point is on one of the edges.
            if x3 == x4:
                return QtCore.QPoint(x3, min(max(0, y2), max(y3, y4)))
            else:  # y3 == y4
                return QtCore.QPoint(min(max(0, x2), max(x3, x4)), y3)
        return QtCore.QPoint(x, y)

    def intersectingEdges(self, point1, point2, points):
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

    # ----------尺寸策略----------#

    # These two, along with a call to adjustSize are required for the
    # scroll area.
    def sizeHint(self):
        return self.minimumSizeHint()

    def minimumSizeHint(self):
        if self.pixmap:
            return self.scale * self.pixmap.size()
        return super(Canvas, self).minimumSizeHint()

    # undo相关功能
    def setLastLabel(self, text, flags):
        assert text
        self.annotations[-1].label = text
        self.annotations[-1].flags = flags
        self.annotataions_backups.pop()
        self.store_annotations()
        return self.annotations[-1]

    def undoLastLine(self):
        assert self.annotations
        self.current = self.annotations.pop()
        self.current.setOpen()
        if self.create_type in ['polygon', 'linestrip']:
            self.line.points = [self.current[-1], self.current[0]]
        elif self.create_type in ['rectangle', 'line', 'circle']:
            self.current.points = self.current.points[0:1]
        elif self.create_type == 'point':
            self.current = None
        self.drawingPolygon.emit(True)

    def undoLastPoint(self):
        if not self.current or self.current.isClosed():
            return
        self.current.popPoint()
        if len(self.current) > 0:
            self.line[0] = self.current[-1]
        else:
            self.current = None
            self.drawingPolygon.emit(False)
        self.repaint()

    def loadPixmap(self, pixmap):
        self.pixmap = pixmap
        self.annotations = []
        self.repaint()

    def loadShapes(self, shapes, replace=True):
        if replace:
            self.annotations = list(shapes)
        else:
            self.annotations.extend(shapes)
        self.store_annotations()
        self.current = None
        self.repaint()

    def setShapeVisible(self, shape, value):
        self.visible[shape] = value
        self.repaint()

    def resetState(self):
        self.restore_cursor()
        self.pixmap = None
        self.annotataions_backups = []
        self.update()

    # 各种状态下的鼠标移动事件
    def mouseMoveEvent(self, ev):
        """Update line with last point and current coordinates."""
        print('move')
        try:
            pos = self.transformPos(ev.localPos())
        except AttributeError:
            return

        self.prevMovePoint = pos
        self.restore_cursor()

        # 新建标记状态下的移动
        if self.create_mode:
            self.line.shape_type = self.create_type

            self.override_cursor(CURSOR_DRAW)
            if not self.current:
                return

            color = self.lineColor
            if self.is_out_of_pixmap(pos):
                # Don't allow the user to draw outside the pixmap.
                # Project the point to the pixmap's edges.
                pos = self.intersectionPoint(self.current[-1], pos)
            elif len(self.current) > 1 and self.create_type == 'polygon' and \
                    self.is_close_enough(pos, self.current[0]):
                # Attract line to starting point and
                # colorise to alert the user.
                pos = self.current[0]
                color = self.current.line_color
                self.override_cursor(CURSOR_POINT)
                self.current.highlightVertex(0, Annotation.NEAR_VERTEX)
            if self.create_type in ['polygon', 'linestrip']:
                self.line[0] = self.current[-1]
                self.line[1] = pos
            elif self.create_type == 'rectangle':
                self.line.points = [self.current[0], pos]
                self.line.close()
            elif self.create_type == 'circle':
                self.line.points = [self.current[0], pos]
                self.line.shape_type = "circle"
            elif self.create_type == 'line':
                self.line.points = [self.current[0], pos]
                self.line.close()
            elif self.create_type == 'point':
                self.line.points = [self.current[0]]
                self.line.close()
            self.line.line_color = color
            self.repaint()
            self.current.highlightClear()
            return

        # MYCODE: 增加通过按住ctrl和鼠标左键移动鼠标调整窗位窗宽的事件
        # 编辑状态下按住ctrl的左键移动
        if QtCore.Qt.LeftButton & ev.buttons():
            mods = ev.modifiers()
            if QtCore.Qt.ControlModifier == int(mods):
                if self.prevprevMovePoint:
                    delta_x = self.prevMovePoint.x() - self.prevprevMovePoint.x()
                    delta_y = self.prevMovePoint.y() - self.prevprevMovePoint.y()
                    self.wlwwRequest.emit(-delta_y * 0.8, delta_x)
                self.prevprevMovePoint = self.prevMovePoint

        # 编辑状态下的右键移动（copy-moving状态）
        if QtCore.Qt.RightButton & ev.buttons():
            if self.selected_shapes_copy and self.prevPoint:
                self.override_cursor(CURSOR_MOVE)
                self.boundedMoveShapes(self.selected_shapes_copy, pos)
                self.repaint()
            elif self.selected_shapes:
                self.selected_shapes_copy = \
                    [s.copy() for s in self.selected_shapes]
                self.repaint()
            return

        # 标记/顶点的左键移动
        self.movingShape = False
        if QtCore.Qt.LeftButton & ev.buttons():
            if self.hVertex is not None:
                self.boundedMoveVertex(pos)
                self.repaint()
                self.movingShape = True
            elif self.selected_shapes and self.prevPoint:
                self.override_cursor(CURSOR_MOVE)
                self.boundedMoveShapes(self.selected_shapes, pos)
                self.repaint()
                self.movingShape = True
            return

        # 移动后悬停时
        # - Highlight annotations
        # - Highlight vertex
        # Update shape/vertex fill and tooltip value accordingly.
        self.setToolTip("Image")
        for shape in reversed(
                [s for s in self.annotations if self.is_shape_visible(s)]):
            # Look for a nearby vertex to highlight. If that fails,
            # check if we happen to be inside a shape.
            index = shape.nearestVertex(pos, self.epsilon / self.scale)
            index_edge = shape.nearestEdge(pos, self.epsilon / self.scale)
            if index is not None:
                if self.hVertex is not None:
                    self.hShape.highlightClear()
                self.hVertex = index
                self.hShape = shape
                self.hEdge = index_edge
                shape.highlightVertex(index, shape.MOVE_VERTEX)
                self.override_cursor(CURSOR_POINT)
                self.setToolTip("Click & drag to move point")
                self.setStatusTip(self.toolTip())
                self.update()
                break
            elif shape.containsPoint(pos):
                if self.hVertex is not None:
                    self.hShape.highlightClear()
                self.hVertex = None
                self.hShape = shape
                self.hEdge = index_edge
                self.setToolTip(
                    "Click & drag to move shape '%s'" % shape.label)
                self.setStatusTip(self.toolTip())
                self.override_cursor(CURSOR_GRAB)
                self.update()
                break
        else:  # Nothing found, clear highlights, reset state.
            if self.hShape:
                self.hShape.highlightClear()
                self.update()
            self.hVertex, self.hShape, self.hEdge = None, None, None
        self.edgeSelected.emit(self.hEdge is not None)

    # 各种状态下的鼠标按键事件
    def mousePressEvent(self, ev):
        pos = self.transformPos(ev.localPos())
        # 按下左键时
        if ev.button() == QtCore.Qt.LeftButton:
            if self.create_mode:
                if self.current:
                    # Add point to existing shape.
                    if self.create_type == 'polygon':
                        self.current.addPoint(self.line[1])
                        self.line[0] = self.current[-1]
                        if self.current.isClosed():
                            self.finalise()
                    elif self.create_type in ['rectangle', 'circle', 'line']:
                        assert len(self.current.points) == 1
                        self.current.points = self.line.points
                        self.finalise()
                    elif self.create_type == 'linestrip':
                        self.current.addPoint(self.line[1])
                        self.line[0] = self.current[-1]
                        if int(ev.modifiers()) == QtCore.Qt.ControlModifier:
                            self.finalise()
                elif not self.is_out_of_pixmap(pos):
                    # Create new shape.
                    self.current = Annotation(shape_type=self.create_type)
                    self.current.addPoint(pos)
                    if self.create_type == 'point':
                        self.finalise()
                    else:
                        if self.create_type == 'circle':
                            self.current.shape_type = 'circle'
                        self.line.points = [pos, pos]
                        self.setHiding()
                        self.drawingPolygon.emit(True)
                        self.update()
            else:
                group_mode = (int(ev.modifiers()) == QtCore.Qt.ControlModifier)
                self.selectShapePoint(pos, multiple_selection_mode=group_mode)
                self.prevPoint = pos
                self.repaint()

        elif ev.button() == QtCore.Qt.RightButton and not self.create_mode:
            group_mode = (int(ev.modifiers()) == QtCore.Qt.ControlModifier)
            self.selectShapePoint(pos, multiple_selection_mode=group_mode)
            self.prevPoint = pos
            self.repaint()

    # 鼠标松开事件
    def mouseReleaseEvent(self, ev):
        self.prevprevMovePoint = None
        if ev.button() == QtCore.Qt.RightButton:
            menu = self.menus[len(self.selected_shapes_copy) > 0]
            self.restore_cursor()
            if not menu.exec_(self.mapToGlobal(ev.pos())) \
                    and self.selected_shapes_copy:
                # Cancel the move by deleting the shadow copy.
                self.selected_shapes_copy = []
                self.repaint()
        elif ev.button() == QtCore.Qt.LeftButton and self.selected_shapes:
            self.override_cursor(CURSOR_GRAB)
        if self.movingShape:
            self.store_annotations()
            self.shapeMoved.emit()

    # 鼠标滚轮事件
    def wheelEvent(self, ev):
        mods = ev.modifiers()
        delta = ev.angleDelta()
        if QtCore.Qt.ControlModifier == int(mods):
            # with Ctrl/Command key
            # zoom
            self.zoomRequest.emit(delta.y(), ev.pos())
        else:
            # scroll
            self.scrollRequest.emit(delta.x(), QtCore.Qt.Horizontal)
            self.scrollRequest.emit(delta.y(), QtCore.Qt.Vertical)
        ev.accept()

    # 键盘事件
    def keyPressEvent(self, ev):
        key = ev.key()
        # Esc键，取消当前标记绘制
        if key == QtCore.Qt.Key_Escape and self.current:
            self.current = None
            self.drawingPolygon.emit(False)
            self.update()
        # 回车键，完成当前标记绘制
        elif key == QtCore.Qt.Key_Shift and self.is_current_shape_finalizable():
            self.finalise()

    # TODO: 探明绘图事件的触发条件
    #  1. 窗口第一次显示
    #  2。窗口大小变化
    #  3. 窗口被遮挡又被显示
    #  4. update()在Qt下一次处理事件时调用一次绘图事件
    #  5. repaint()立刻调用一次绘图事件
    def paintEvent(self, event):
        if not self.pixmap:
            return super(Canvas, self).paintEvent(event)

        p = self._painter
        p.begin(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.setRenderHint(QtGui.QPainter.HighQualityAntialiasing)
        p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)

        p.scale(self.scale, self.scale)
        p.translate(self.offsetToCenter())

        p.drawPixmap(0, 0, self.pixmap)
        Annotation.scale = self.scale
        # 标记的绘制
        for shape in self.annotations:
            if (shape.selected or not self._hideBackround) and \
                    self.is_shape_visible(shape):
                shape.fill = shape.selected or shape == self.hShape
                shape.paint(p)
        if self.current:
            self.current.paint(p)
            self.line.paint(p)
        if self.selected_shapes_copy:
            for s in self.selected_shapes_copy:
                s.paint(p)

        if (self.fill_shape and self.create_type == 'polygon' and
                self.current is not None and len(self.current.points) >= 2):
            drawing_shape = self.current.copy()
            drawing_shape.addPoint(self.line[1])
            drawing_shape.fill = True
            drawing_shape.fill_color.setAlpha(64)
            drawing_shape.paint(p)

        p.end()

    def unHighlight(self):
        if self.hShape:
            self.hShape.highlightClear()
        self.hVertex = self.hShape = None



if __name__ == '__main__':
    import sys
    from pycallgraph import PyCallGraph
    from pycallgraph.output import GraphvizOutput
    from pycallgraph import Config
    from pycallgraph import GlobbingFilter

    graphviz = GraphvizOutput()
    graphviz.output_file = 'basic.png'
    config = Config()
    print(config)

    with PyCallGraph(output=graphviz, config=config):
        app = QtWidgets.QApplication(sys.argv)
        window = QtWidgets.QMainWindow()
        window.setCentralWidget(Canvas())
        window.show()
        sys.exit(app.exec_())

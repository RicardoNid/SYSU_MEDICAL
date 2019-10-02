'''
实现Annotation数据类，对应于标注，其内容包括
属性：

方法：

'''

import copy
import math

from qtpy import QtCore
from qtpy import QtGui

import labelme.utils

# TODO(unknown):
# - [opt] Store paths instead of creating new ones at each paint.

DEFAULT_LINE_COLOR = QtGui.QColor(0, 255, 0, 128)
DEFAULT_FILL_COLOR = QtGui.QColor(255, 0, 0, 128)
DEFAULT_SELECT_LINE_COLOR = QtGui.QColor(255, 255, 255)
DEFAULT_SELECT_FILL_COLOR = QtGui.QColor(0, 128, 255, 155)
DEFAULT_VERTEX_FILL_COLOR = QtGui.QColor(0, 255, 0, 255)
DEFAULT_HVERTEX_FILL_COLOR = QtGui.QColor(255, 0, 0)


class Annotation(object):
    # FIXME: 调试用属性，打包/发布前删除

    # 下面的属性与常量都是类属性
    P_SQUARE, P_ROUND = 0, 1

    MOVE_VERTEX, NEAR_VERTEX = 0, 1

    # 类属性为对象属性提供了默认值，会被同名对象属性覆盖
    # shape边框颜色
    line_color = DEFAULT_LINE_COLOR
    # shape填充颜色
    fill_color = DEFAULT_FILL_COLOR

    select_line_color = DEFAULT_SELECT_LINE_COLOR
    select_fill_color = DEFAULT_SELECT_FILL_COLOR
    vertex_fill_color = DEFAULT_VERTEX_FILL_COLOR
    hvertex_fill_color = DEFAULT_HVERTEX_FILL_COLOR

    # 顶点参数，包括形状，尺寸
    point_type = P_ROUND
    point_size = 8

    #
    scale = 1.0

    def __init__(self, label=None, line_color=None, shape_type=None,
                 flags=None):
        # 数据属性：点，标签（只能有一个）和标志（可以有多个）
        self.points = []
        self.label = label
        self.flags = flags
        self.disease_specific_label = {}

        # 状态属性
        self.selected = False
        self.fill = False
        self._closed = False
        self.shape_type = shape_type
        # TODO: 补充注释
        self._highlightIndex = None
        self._highlightMode = self.NEAR_VERTEX
        self._highlightSettings = {
            self.NEAR_VERTEX: (4, self.P_ROUND),
            self.MOVE_VERTEX: (1.5, self.P_SQUARE),
        }

        if line_color is not None:
            self.line_color = line_color

    # ----------property属性----------#
    @property
    def shape_type(self):
        return self._shape_type

    @shape_type.setter
    # 通过setter进行赋值控制
    def shape_type(self, value):
        if value is None:
            value = 'polygon'
        if value not in ['polygon', 'rectangle', 'point',
                         'line', 'circle', 'linestrip']:
            raise ValueError('Unexpected shape_type: {}'.format(value))
        self._shape_type = value

    # ----------重载魔术方法----------#
    def __len__(self):
        return len(self.points)

    # 重载索引方法
    def __getitem__(self, key):
        return self.points[key]

    # 重载索引赋值方法
    def __setitem__(self, key, value):
        self.points[key] = value

    # -----------查询和设置_closed属性----------#
    def close(self):
        self._closed = True

    def setOpen(self):
        self._closed = False

    def isClosed(self):
        return self._closed

    # ----------编辑shape中的点----------#
    def addPoint(self, point):
        if self.points and point == self.points[0]:
            self.close()
        else:
            self.points.append(point)

    def popPoint(self):
        if self.points:
            # question: 应该setOpen？
            self.setOpen()
            return self.points.pop()
        return None

    def insertPoint(self, i, point):
        self.points.insert(i, point)

    # -----------获取临近顶点和边----------#
    def nearestVertex(self, point, epsilon):
        '''返回shape中离point最近的的顶点的序号，距离需要小于epsilon，若没有则返回None'''
        min_distance = float('inf')
        min_i = None
        for i, p in enumerate(self.points):
            # FIXME: 想办法替代distance方法
            dist = labelme.utils.distance(p - point)
            if dist <= epsilon and dist < min_distance:
                min_distance = dist
                min_i = i
        return min_i

    def nearestEdge(self, point, epsilon):
        '''返回shape中离point最近的的边的序号，距离需要小于epsilon，若没有则返回None'''
        min_distance = float('inf')
        post_i = None
        for i in range(len(self.points)):
            line = [self.points[i - 1], self.points[i]]
            dist = labelme.utils.distancetoline(point, line)
            if dist <= epsilon and dist < min_distance:
                min_distance = dist
                post_i = i
        return post_i

    # -----------构造QPainterPath对象----------#
    # 构造这个对象是为了调用其在Qt中的方法实现包含检查和boundbox生成
    # question: 改写为property？
    def makePath(self):
        if self.shape_type == 'rectangle':
            path = QtGui.QPainterPath()
            if len(self.points) == 2:
                rectangle = self.getRectFromLine(*self.points)
                path.addRect(rectangle)
        elif self.shape_type == "circle":
            path = QtGui.QPainterPath()
            if len(self.points) == 2:
                rectangle = self.getCircleRectFromLine(self.points)
                path.addEllipse(rectangle)
        else:
            path = QtGui.QPainterPath(self.points[0])
            for p in self.points[1:]:
                path.lineTo(p)
        return path

    # 获取shape的boundingbox
    def boundingRect(self):
        return self.makePath().boundingRect()

    def containsPoint(self, point):
        return self.makePath().contains(point)

    # -----------获取矩形和被圆内切的矩形RectF对象----------#
    # insight: 这两个方法的目的也是获取shape的boundingbox，
    #   因为矩形和圆的模型异于其他，不能被QPainterPath涵盖，所以专门实现
    def getRectFromLine(self, pt1, pt2):
        x1, y1 = pt1.x(), pt1.y()
        x2, y2 = pt2.x(), pt2.y()
        return QtCore.QRectF(x1, y1, x2 - x1, y2 - y1)

    def getCircleRectFromLine(self, line):
        """Computes parameters to draw with `QPainterPath::addEllipse`"""
        if len(line) != 2:
            return None
        (c, point) = line
        r = line[0] - line[1]
        d = math.sqrt(math.pow(r.x(), 2) + math.pow(r.y(), 2))
        rectangle = QtCore.QRectF(c.x() - d, c.y() - d, 2 * d, 2 * d)
        return rectangle

    # -----------进行绘制----------#
    # question: 需要学习qt painter机制？
    def paint(self, painter):
        if self.points:
            color = self.select_line_color \
                if self.selected else self.line_color

            # 配置painter
            pen = QtGui.QPen(color)
            # Try using integer sizes for smoother drawing(?)
            pen.setWidth(max(1, int(round(2.0 / self.scale))))
            painter.setPen(pen)

            line_path = QtGui.QPainterPath()
            vrtx_path = QtGui.QPainterPath()

            if self.shape_type == 'rectangle':
                assert len(self.points) in [1, 2]
                if len(self.points) == 2:
                    rectangle = self.getRectFromLine(*self.points)
                    line_path.addRect(rectangle)
                for i in range(len(self.points)):
                    self.drawVertex(vrtx_path, i)

            elif self.shape_type == "circle":
                assert len(self.points) in [1, 2]
                if len(self.points) == 2:
                    rectangle = self.getCircleRectFromLine(self.points)
                    line_path.addEllipse(rectangle)
                for i in range(len(self.points)):
                    self.drawVertex(vrtx_path, i)

            elif self.shape_type == "linestrip":
                line_path.moveTo(self.points[0])
                for i, p in enumerate(self.points):
                    line_path.lineTo(p)
                    self.drawVertex(vrtx_path, i)
            else:
                line_path.moveTo(self.points[0])
                # Uncommenting the following line will draw 2 paths
                # for the 1st vertex, and make it non-filled, which
                # may be desirable.
                # self.drawVertex(vrtx_path, 0)

                for i, p in enumerate(self.points):
                    line_path.lineTo(p)
                    self.drawVertex(vrtx_path, i)
                if self.isClosed():
                    line_path.lineTo(self.points[0])

            painter.drawPath(line_path)
            painter.drawPath(vrtx_path)
            painter.fillPath(vrtx_path, self.vertex_fill_color)
            if self.fill:
                color = self.select_fill_color \
                    if self.selected else self.fill_color
                painter.fillPath(line_path, color)

    def drawVertex(self, path, i):
        d = self.point_size / self.scale
        shape = self.point_type
        point = self.points[i]
        if i == self._highlightIndex:
            size, shape = self._highlightSettings[self._highlightMode]
            d *= size
        if self._highlightIndex is not None:
            self.vertex_fill_color = self.hvertex_fill_color
        else:
            self.vertex_fill_color = Annotation.vertex_fill_color
        if shape == self.P_SQUARE:
            path.addRect(point.x() - d / 2, point.y() - d / 2, d, d)
        elif shape == self.P_ROUND:
            path.addEllipse(point, d / 2.0, d / 2.0)
        else:
            assert False, "unsupported vertex shape"

    # ----------高亮操作----------#
    def highlightVertex(self, i, action):
        self._highlightIndex = i
        self._highlightMode = action

    def highlightClear(self):
        self._highlightIndex = None

    # ----------复制和移动操作----------#
    def copy(self):
        return copy.deepcopy(self)

    def moveBy(self, offset):
        self.points = [p + offset for p in self.points]

    def moveVertexBy(self, i, offset):
        self.points[i] = self.points[i] + offset

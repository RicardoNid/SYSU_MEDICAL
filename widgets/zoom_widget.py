from PyQt5 import QtWidgets
from PyQt5 import QtCore
from PyQt5 import QtGui

class ZoomWidget(QtWidgets.QSpinBox):
    '''zoom_action的动作窗口，所有的缩放动作都通过设置该窗口上的缩放比例值触发进行'''

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
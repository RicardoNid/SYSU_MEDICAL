from PyQt5 import QtWidgets
from PyQt5 import QtCore
from PyQt5 import QtGui

class WlwwWidget(QtWidgets.QWidget):
    '''wlww_action的动作窗口，所有对于窗位窗宽的调整都通过设置该窗口上的窗位窗宽值触发进行'''

    wlww_changed_signal = QtCore.pyqtSignal(int, int)

    def __init__(self):
        super(WlwwWidget,self).__init__()
        self.layout = QtWidgets.QHBoxLayout()

        self.wl_lable = QtWidgets.QLabel('窗位')
        self.wl_spin = QtWidgets.QSpinBox()
        self.wl_spin.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        self.wl_spin.setRange(-1024, 1024)
        self.wl_spin.setValue(-600)
        self.wl_spin.setAlignment(QtCore.Qt.AlignCenter)
        self.wl_spin.valueChanged.connect(self.wlww_changed)

        self.ww_lable = QtWidgets.QLabel('窗宽')
        self.ww_spin = QtWidgets.QSpinBox()
        self.ww_spin.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        self.ww_spin.setRange(0, 5000)
        self.ww_spin.setValue(1200)
        self.ww_spin.setAlignment(QtCore.Qt.AlignCenter)
        self.ww_spin.valueChanged.connect(self.wlww_changed)

        self.layout.addWidget(self.wl_lable)
        self.layout.addWidget(self.wl_spin)
        self.layout.addWidget(self.ww_lable)
        self.layout.addWidget(self.ww_spin)
        self.setLayout(self.layout)

    def wlww_changed(self):
        self.wlww_changed_signal.emit(self.wl_spin.value(), self.ww_spin.value())

    def minimumSizeHint(self):
        height = super(WlwwWidget, self).minimumSizeHint().height()
        fm = QtGui.QFontMetrics(self.font())
        width = fm.width(str(self.wl_spin.maximum()) * 2)
        return QtCore.QSize(width, height)

if __name__ == '__main__':
    import sys

    app = QtWidgets.QApplication(sys.argv)
    window = WlwwWidget()
    window.show()
    sys.exit(app.exec_())






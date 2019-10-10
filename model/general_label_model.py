from PyQt5 import QtWidgets
from PyQt5 import QtGui
from PyQt5 import QtCore

import json
import xml.dom.minidom as xml

from typing import Tuple, List, Dict

class GeneralLabel():
    def __init__(self):
        pass

    def save(self):
        pass

    def load(self):
        pass

class GeneralAttribute():
    def __init__(self):
        self.name = ''
        self.type = 'value'
        self.is_necessary = True
        self.enum_list = []

    @property
    def type(self):
        return self._type

    @type.setter
    def type(self, value):
        if value not in ['value', 'bool', 'enum']:
            return False
        else: self._type = value

    @property
    def is_necessary(self):
        return self._is_nesscessary

    @is_necessary.setter
    def is_necessary(self, value):
        if not isinstance(value, bool):
            return False
        else: self._is_necessary = value

class GeneralLabelGenerator():
    '''
    通用标签模型的工作方式如下
    用配置文件或配置参数初始化通用标签生成器，配置文件或配置参数需要通过合法性检查
    初始化成功后，用户可以利用通用标签生成器的方法，生产符合配置文件或配置参数所限定规则的
        1.通用标签对象
        2.通用标签对象输入窗口对象
        3.输出通用标签文件
    '''
    def __init__(self):
        self.name = ''

    def generate_label(self) -> GeneralLabel:
        return GeneralLabel()

    def generate_widget(self):
        pass

class GeneralLabelConfig():
    def __init__(self):
        self.name = ''
        self.attributes_list = []

    def add_attribute(self, attr: GeneralAttribute) -> None:
        self.attributes_list.append(attr)

class GeneralLabelWidget(QtWidgets.QWidget):
    def __init__(self, config: GeneralLabelConfig):
        super(GeneralLabelWidget, self).__init__()
        self.config = config
        print(config.attributes_list[0])

        self.layout = QtWidgets.QVBoxLayout()
        for attr in self.config.attributes_list:
            label = QtWidgets.QLabel(attr.name)
            self.layout.addWidget(label)
            if attr.type == 'value':
                widget = QtWidgets.QSpinBox()
                widget.setObjectName(attr.name)
                self.layout.addWidget(widget)
            elif attr.type == 'bool':
                widget = QtWidgets.QCheckBox()
                widget.setObjectName(attr.name)
            elif attr.type == 'enum':
                layout = QtWidgets.QHBoxLayout()
                for enum_item in attr.enum_list:
                    widget = QtWidgets.QRadioButton(enum_item)
                    widget.setObjectName(attr.name + '_' + enum_item)
                    layout.addWidget(widget)
                self.layout.addLayout(layout)
        self.setLayout(self.layout)

if __name__ == '__main__':
    pass


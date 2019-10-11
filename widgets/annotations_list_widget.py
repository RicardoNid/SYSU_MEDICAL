'''
实现标记列表控件，列出当前图像中所有标记名称及可见性，提供标记选择和可见性修改功能，
占据MainWindow的一个浮动子窗口
'''

from common_import import *

# 用于支持复合type-hint
from typing import List

from annotations import Annotation

class AnnotationsListWidget(QListWidget):
    def __init__(self):
        super(AnnotationsListWidget, self).__init__()

        self.annotations = []

        self.init_content()

    def init_content(self):

        self.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.setSelectionMode(QAbstractItemView.SingleSelection)

    def refresh(self, annotations: List[Annotation]) -> None:
        self.clear()
        self.annotations = annotations
        for i, annotation in enumerate(self.annotations):
            self.addItem(annotation.annotation_type)
            self.item(i).setCheckState(annotation.is_visable)




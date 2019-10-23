'''
实现标记列表控件，列出当前图像中所有标记名称及可见性，提供标记选择和可见性修改功能，
占据MainWindow的一个浮动子窗口
'''

from common_import import *

# 用于支持复合type-hint
from typing import List

class SeriesListWidget(QListWidget):
    def __init__(self):
        super(SeriesListWidget, self).__init__()
        self.files = []
        self.init_content()

    def init_content(self):

        self.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.setSelectionMode(QAbstractItemView.SingleSelection)

    def refresh_files(self, files: List[str]) -> None:
        self.clear()
        self.files = files
        self.refresh()

    def refresh(self):
        for file in self.files:
            self.addItem(file)

    def change_current_item_slot(self, value: int):
        new_row = self.currentRow() + value
        new_row = max(new_row, 0)
        new_row = min(new_row, self.count() - 1)
        self.setCurrentRow(new_row)






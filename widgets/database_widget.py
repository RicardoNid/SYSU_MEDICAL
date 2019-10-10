'''
实现数据库控件
占据MainWindow的一个浮动子窗口
'''
from common_import import *

import pydicom
from xml.etree.ElementTree import ElementTree,Element

from datatypes import DicomTree
from ui import Ui_DatabaseWidget

# 用于支持复合type-hint
from typing import List

from annotations import Annotation

class DatabaseWidget(QWidget, Ui_DatabaseWidget):
    def __init__(self, parent=None):
        super(DatabaseWidget, self).__init__(parent)
        self.setupUi(self)

        self.dicom_tree = DicomTree()
        self.dicom_tree._root = Element('database')

        self.init_content()

        self.new_database_button.clicked.connect(partial(self.new_database_slot, None, None))

    def new_database_slot(self, dir_path: str, database_name: str) -> None:
        '''在指定目录下递归搜索所有dicom文件，按照 的等级构成树结构'''
        dir_path = r'Y:\MRI\demo\10149857'
        database_name = 'MRI数据库'
        new_database = DicomTree.load_from_dir(dir_path, database_name)
        self.dicom_tree._root.append(new_database.getroot())
        self.refresh()

    def init_content(self):
        '''初始化显示'''
        self.database_tree_widget.setColumnCount(3)

        # self.database_tree_widget.setHeaderHidden(True)
        self.database_tree_widget.setSelectionBehavior(QAbstractItemView.SelectRows)
        # question: 哪种选择模式比较好？
        self.database_tree_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)

        header = QTreeWidgetItem()
        header.setText(0, '描述')
        header.setText(1, 'uid/id')
        header.setText(2, '文件路径')
        self.database_tree_widget.setHeaderItem(header)
        self.root_item = QTreeWidgetItem(self.database_tree_widget)
        self.root_item.setText(0, '数据库列表')

    def refresh(self):
        '''根据DicomTree的内容刷新显示'''
        # self.database_tree_widget.clear()
        self.build_tree_recursively(self.root_item, self.dicom_tree.getroot())

    def close(self):
        pass

    def build_tree_recursively(self, tree_widget_item: QTreeWidgetItem, dicom_tree_element: Element):
        # 没有子元素时，递归结束
        if not list(dicom_tree_element):
            return
        else:
            for child_element in list(dicom_tree_element):
                text_list = []
                if child_element.tag == 'database':
                    text_list = [child_element.attrib['name'], '', '']
                elif child_element.tag == 'patient':
                    text_list = [child_element.attrib['id']+ child_element.attrib['name'], '', '']
                elif child_element.tag == 'study':
                    text_list = ['study: ' + child_element.attrib['date'], child_element.attrib['uid'], '']
                elif child_element.tag == 'series':
                    text_list = ['series' + child_element.attrib['number'] + ':' +
                                 child_element.attrib['description'],
                                 child_element.attrib['uid'], '']
                elif child_element.tag == 'instance':
                    text_list = [child_element.attrib['number'], child_element.attrib['uid'],
                                 child_element.attrib['path']]
                child_item = QTreeWidgetItem(tree_widget_item)
                child_item.setText(0, text_list[0])
                child_item.setText(1, text_list[1])
                child_item.setText(2, text_list[2])
                # 递归调用
                self.build_tree_recursively(child_item, child_element)

                self.database_tree_widget.resizeColumnToContents(0)
                self.database_tree_widget.resizeColumnToContents(1)
                self.database_tree_widget.resizeColumnToContents(2)

if __name__ == '__main__':
    import sys

    app = QApplication(sys.argv)
    window = DatabaseWidget()
    window.show()
    sys.exit(app.exec_())





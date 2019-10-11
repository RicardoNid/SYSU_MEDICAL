'''
实现数据库控件
占据MainWindow的一个浮动子窗口
'''
from common_import import *
import pydicom
from xml.etree.ElementTree import ElementTree,Element

from datatypes import DicomTree
from utils import *

# 用于支持复合type-hint
from typing import List

class DatabaseWidget(QWidget):

    DATABASE_PATH = osp.abspath(r'database')
    series_selected_signal = pyqtSignal(List[str])

    def __init__(self, parent=None):
        super(DatabaseWidget, self).__init__(parent)

        self.dicom_trees = []

        self.init_ui()
        self.init_content()

    def init_ui(self):
        self.layout = QGridLayout()
        self.database_tree_widget = QTreeWidget()
        self.layout.addWidget(self.database_tree_widget)
        self.setLayout(self.layout)

    def new_database(self, dir_path: str, database_name: str) -> None:
        '''在指定目录下递归搜索所有dicom文件，构成DicomTree，加载到数据库窗口并保存'''
        # 检查数据库名称合法性
        if database_name in [dicom_tree.getroot().attrib['name'] for
                             dicom_tree in self.dicom_trees]:
            QMessageBox.warning(self, '非法输入', '已经存在同名数据库')
            return

        new_database = DicomTree.load_from_dir(dir_path, database_name)
        new_database.write(osp.join(self.DATABASE_PATH, '%s.xml'%(database_name)),
                           encoding='utf-8',xml_declaration=True)
        self.dicom_trees.append(new_database)
        self.refresh()

    def init_databases(self):
        databases = [osp.join(self.DATABASE_PATH, database) for database
                     in os.listdir(self.DATABASE_PATH)
                     if database.endswith('.xml')]
        self.dicom_trees = [DicomTree.load(database) for database in databases]

    def init_content(self):
        '''初始化显示'''
        # 设置树控件
        self.database_tree_widget.setColumnCount(3)
        # self.database_tree_widget.setHeaderHidden(True)
        self.database_tree_widget.setSelectionBehavior(QAbstractItemView.SelectRows)
        # question: 哪种选择模式比较好？
        self.database_tree_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.database_tree_widget.setHeaderLabels(['内容', 'uid/id', '文件路径'])
        # TODO: 更好的显示方案
        self.database_tree_widget.hideColumn(1)
        # self.database_tree_widget.hideColumn(2)
        self.database_tree_widget.setColumnWidth(0, 200)
        # 读取和显示现有数据库
        self.init_databases()
        self.refresh()

    def refresh(self):
        '''根据DicomTree的内容刷新显示'''
        self.database_tree_widget.clear()
        for database in self.dicom_trees:
            root_item = QTreeWidgetItem()
            root_item.setText(0, database.getroot().attrib['name'])
            self.build_tree_recursively(root_item, database.getroot())
            self.database_tree_widget.resizeColumnToContents(0)
            self.database_tree_widget.addTopLevelItem(root_item)

    def build_tree_recursively(self, tree_widget_item: QTreeWidgetItem, dicom_tree_element: Element):
        # 在series层递归结束
        if dicom_tree_element.tag == 'series':
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
                    # 对于seires，如果其中instance都来自同一目录，显示目录路径为其文件路径
                    dir = ''
                    for instance in list(child_element):
                        if dir and dir != osp.dirname(instance.attrib['path']):
                            print('前后路径', dir, osp.dirname(instance.attrib['path']))
                            break
                        dir = osp.dirname(instance.attrib['path'])
                    else:
                        text_list[2] = dir
                # elif child_element.tag == 'instance':
                #     text_list = [child_element.attrib['number'], child_element.attrib['uid'],
                #                  child_element.attrib['path']]
                child_item = QTreeWidgetItem(tree_widget_item)
                child_item.setText(0, text_list[0])
                child_item.setText(1, text_list[1])
                child_item.setText(2, text_list[2])
                # 递归调用
                self.build_tree_recursively(child_item, child_element)

                self.database_tree_widget.resizeColumnToContents(0)
                self.database_tree_widget.resizeColumnToContents(1)
                self.database_tree_widget.resizeColumnToContents(2)

    def mouseDoubleClickEvent(self, ev):
        print('double click triggered')
        path = self.database_tree_widget.currentItem.text(2)
        # 如果选中的条目有文件路径
        if path:
            files = get_dicom_files_path_from_dir(path)
            self.series_selected_signal(files)

if __name__ == '__main__':
    import sys

    app = QApplication(sys.argv)
    window = DatabaseWidget()
    window.show()
    sys.exit(app.exec_())





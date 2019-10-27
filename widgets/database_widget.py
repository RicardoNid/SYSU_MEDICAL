'''
实现数据库控件
占据MainWindow的一个浮动子窗口
'''
from xml.etree.ElementTree import Element

from datatypes import DicomTree
from utils import *
from typing import *

# 用于支持复合type-hint

class DatabaseWidget(QTreeWidget):

    DATABASE_PATH = osp.abspath(r'database')
    series_selected_signal = pyqtSignal(list)

    def __init__(self, parent=None):
        super(DatabaseWidget, self).__init__(parent)

        self.dicom_trees = []
        self.init_content()

    def init_content(self):
        '''初始化显示'''
        # 设置树控件
        self.setColumnCount(3)
        # self.setHeaderHidden(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        # question: 哪种选择模式比较好？
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setHeaderLabels(['内容', 'uid/id', '文件路径'])
        # TODO: 更好的显示方案
        self.hideColumn(1)
        self.hideColumn(2)
        # 读取和显示现有数据库
        self.init_databases()
        self.refresh()
        # 初始状态下展开到series级别
        self.expandToDepth(2)

    def init_databases(self):
        self.databases = [osp.join(self.DATABASE_PATH, database) for database
                          in os.listdir(self.DATABASE_PATH)
                          if database.endswith('.xml')]
        self.dicom_trees = [DicomTree.load(database) for database in self.databases]

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
        self.expandToDepth(2)

    def add_to_database(self, database_id: int, fps: list) -> None:
        dicom_tree = self.dicom_trees[database_id]
        dicom_tree.add_files(fps)
        dicom_tree.save(self.databases[database_id])
        self.refresh()

    def refresh(self):
        '''根据DicomTree的内容刷新显示'''
        self.clear()
        for database in self.dicom_trees:
            root_item = QTreeWidgetItem()
            root_item.setText(0, database.getroot().attrib['name'])
            self.build_tree_recursively(root_item, database.getroot())
            self.addTopLevelItem(root_item)
            self.setColumnWidth(0,400)

    def build_tree_recursively(self, tree_widget_item: QTreeWidgetItem, dicom_tree_element: Element):
        # 在series层递归结束
        if dicom_tree_element.tag == 'series':
            return
        else:
            for child_element in list(dicom_tree_element):
                text_list = []
                if child_element.tag == 'database':
                    text_list = [child_element.attrib['name'],
                                 '',
                                 '']
                elif child_element.tag == 'patient':
                    text_list = ['患者' + child_element.attrib['id'] + ' ' + child_element.attrib['name'],
                                 child_element.attrib['id'],
                                 '']
                elif child_element.tag == 'study':
                    text_list = ['检查: ' + child_element.attrib['date'],
                                 child_element.attrib['uid'],
                                 '']
                elif child_element.tag == 'series':
                    text_list = ['序列' + child_element.attrib['number'] + ': ' + child_element.attrib['description'],
                                 child_element.attrib['uid'],
                                 '']
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
                # insight: 用默认flags和需要的flag按位异或，就能使需要的flag翻转
                child_item.setFlags(child_item.flags() ^ Qt.ItemIsUserCheckable)
                if child_element.tag == 'series' and osp.exists(text_list[2]):
                    for file in os.listdir(text_list[2]):
                        if file.endswith('.pkl'):
                            child_item.setCheckState(0, 1)
                            break
                        else:
                            child_item.setCheckState(0, 0)
                child_item.setText(0, text_list[0])
                child_item.setText(1, text_list[1])
                child_item.setText(2, text_list[2])
                # 递归调用
                self.build_tree_recursively(child_item, child_element)

                self.resizeColumnToContents(0)
                self.resizeColumnToContents(1)
                self.resizeColumnToContents(2)

    def mouseDoubleClickEvent(self, ev):
        # 如果选中的条目是序列
        if '序列' in self.currentItem().text(0):
            files = []
            # 从下往上获取uid，然后用uid在DicomTree上从上往下查找到序列节点，获得其所有实例子节点的路径
            series_uid = self.currentItem().text(1)
            study_uid = self.currentItem().parent().text(1)
            patient_id = self.currentItem().parent().parent().text(1)
            database_name = self.currentItem().parent().parent().parent().text(0)
            print(series_uid, study_uid, patient_id, database_name, sep='\n')

            index = [dicom_tree.getroot().attrib['name'] for dicom_tree in self.dicom_trees].index(database_name)
            dicom_tree = self.dicom_trees[index]
            series_element = dicom_tree.search_by_top_down_uid([patient_id, study_uid, series_uid])
            files = [instance.attrib['path'] for instance in list(series_element)]
            self.series_selected_signal.emit(files)

if __name__ == '__main__':
    import sys

    app = QApplication(sys.argv)
    window = DatabaseWidget()
    window.show()
    sys.exit(app.exec_())





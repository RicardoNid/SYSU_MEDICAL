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

    PATIENT_MARK = '患者'
    STUDY_MARK = '检查'
    SERIES_MARK = '序列'

    DATABASE_PATH = osp.abspath(r'database')
    series_selected_signal = pyqtSignal(list)

    def __init__(self, parent=None):
        super(DatabaseWidget, self).__init__(parent)

        self.dicom_tree = DicomTree()
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
        self.init_database()
        self.refresh()
        # 初始状态下展开到series级别
        self.expandToDepth(2)

    def init_database(self):
        '''
        初始化数据库,数据库来源为
            1.数据库目录下的第一个数据库
            TODO
            2.从config加载的,上一次的数据库
        '''
        self.database = osp.join(self.DATABASE_PATH, os.listdir(self.DATABASE_PATH)[0])
        self.dicom_tree = DicomTree.load(self.database)

    def new_database(self, dir_path: str, database_name: str) -> None:
        '''在指定目录下递归搜索所有dicom文件，构成DicomTree，加载到数据库窗口并保存'''
        # 检查数据库名称合法性
        if database_name in [osp.splitext(file)[0] for file in os.listdir(self.DATABASE_PATH)]:
            QMessageBox.warning(self, '非法输入', '已经存在同名数据库')
            return

        new_database = DicomTree.load_from_dir(dir_path, database_name)
        new_database_path = osp.join(self.DATABASE_PATH, '%s.xml'%(database_name))
        new_database.write(new_database_path, encoding='utf-8',xml_declaration=True)
        self.database = new_database_path
        self.dicom_tree = new_database

        self.refresh()
        self.expandToDepth(2)

    def add_to_database(self, database_id: int, fps: list) -> None:
        self.dicom_tree.add_files(fps)
        self.dicom_tree.save(self.database)
        self.refresh()

    def refresh(self):
        '''根据DicomTree的内容刷新显示'''
        self.clear()
        root_item = QTreeWidgetItem()
        root_item.setText(0, self.dicom_tree.getroot().attrib['name'])
        self.build_tree_recursively(root_item, self.dicom_tree.getroot())
        self.addTopLevelItem(root_item)
        self.setColumnWidth(0,400)


    def build_tree_recursively(self, tree_widget_item: QTreeWidgetItem, dicom_tree_element: Element):
        '''将DicomTree中的内容显示到TreeWidget'''
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
                    text_list = [self.PATIENT_MARK + ': ' + child_element.attrib['id'] + ' ' + child_element.attrib['name'],
                                 child_element.attrib['id'],
                                 '']
                elif child_element.tag == 'study':
                    text_list = [self.STUDY_MARK + ': ' + child_element.attrib['date'],
                                 child_element.attrib['uid'],
                                 '']
                elif child_element.tag == 'series':
                    text_list = [self.SERIES_MARK + ': ' + child_element.attrib['number'] + ': ' + child_element.attrib['description'],
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
                child_item.setFlags(child_item.flags()
                                    ^ Qt.ItemIsAutoTristate)
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
        '''
        双击可选内容来将数据库中的内容打开查看/标记
            1.双击一个series,使其成为"当前序列"
            TODO
            2.双击一个study,使其第一个序列成为"当前序列",其它序列待选
        '''
        if '序列' in self.currentItem().text(0):
            series_element = self.dicom_tree.search_by_top_down_uid(self.get_top_down_uid(self.currentItem()))
            files = [instance.attrib['path'] for instance in list(series_element)]
            self.series_selected_signal.emit(files)

    def get_top_down_uid(self, item):
        '''
        获取一个节点的top-down uid列表,用于dicom_tree的search_by_top_down_uid方法
        返回的uid列表形式如同[patientID studyUID seriesUID instanceUID],根据节点的级别后面的ID可以缺省
        '''
        if self.SERIES_MARK in item.text(0):
            series_uid = item.text(1)
            study_uid = item.parent().text(1)
            patient_id = item.parent().parent().text(1)
        elif self.STUDY_MARK in item.text(0):
            study_uid = item.text(1)
            patient_id = item.parent().text(1)
        elif self.PATIENT_MARK in item.text(0):
            patient_id = item.text(1)

        return[patient_id, study_uid, series_uid]



if __name__ == '__main__':
    import sys

    app = QApplication(sys.argv)
    window = DatabaseWidget()
    window.show()
    sys.exit(app.exec_())





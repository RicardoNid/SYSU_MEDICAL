'''
实现数据库控件
占据MainWindow的一个浮动子窗口
'''

import time

from xml.etree.ElementTree import Element

from datatypes import DicomTree
from dialogs import *
from utils import *
from typing import *

# 用于支持复合type-hint

class DatabaseWidget(QTreeWidget):

    PATIENT_MARK, STUDY_MARK, SERIES_MARK = '患者', '检查', '序列'
    DATABASE_PATH = osp.abspath(r'database')
    series_selected_signal = pyqtSignal(QTreeWidgetItem, list)

####初始化####
    def __init__(self, parent=None):
        super(DatabaseWidget, self).__init__(parent)

        self.dicom_tree = DicomTree()
        self.database = ''
        self.init_content()

    def init_content(self):
        '''初始化显示'''
        # 设置树控件
        self.setColumnCount(5)
        # self.setHeaderHidden(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        # question: 哪种选择模式比较好？
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setHeaderLabels(['内容', 'uid/id', '文件路径', '导入时间', '最后编辑时间'])
        # TODO: 更好的显示方案
        self.hideColumn(1)
        self.hideColumn(2)
        # 读取和显示现有数据库
        self.init_database()
        # 初始状态下展开到series级别
        self.expandToDepth(2)

    def init_database(self):
        '''
        初始化数据库,数据库来源为
            1.数据库目录下的第一个数据库
            TODO
            2.从config加载的,上一次的数据库
        '''
        if os.listdir(self.DATABASE_PATH):
            database_path = osp.join(self.DATABASE_PATH, os.listdir(self.DATABASE_PATH)[0])
            self.open_database(database_path)
####初始化完成####

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

    def open_database(self, database_path: str) -> None:
        self.database = database_path
        self.dicom_tree = DicomTree.load(self.database)
        self.refresh()

    def add_to_database(self, fps: list) -> None:
        '''将.dcm文件加入dicom数据库,过程中显示分析进度条,结束后打开最新的序列'''
        progress = ProgressBar(0, len(fps))
        progress.show()
        # self.dicom_tree.add_files(fps)
        for i, fp in enumerate(fps):
            self.dicom_tree.add_file(fp)
            progress.setValue(i + 1)
            QApplication.processEvents()

        # warning 大型数据库保存的时间代价?
        self.dicom_tree.save(self.database)
        self.refresh()

    def refresh(self):
        '''根据DicomTree的内容刷新显示'''
        self.clear()
        if self.database:
            root_item = QTreeWidgetItem()
            root_item.setText(0, self.dicom_tree.getroot().attrib['name'])
            self.build_tree_recursively(root_item, self.dicom_tree.getroot())
            self.addTopLevelItem(root_item)
            self.setColumnWidth(0,400)

    def expand_recursively(self, item: QTreeWidgetItem):
        '''展开至某特定节点,需要递归地展开其父节点'''
        if item.parent():
            self.expand_recursively(item.parent())
            self.expandItem(item)
        else:
            self.expandItem(item)

    def send_latest_imported_series(self):
        '''将最新导入的序列发送给外部窗口'''
        latest_time = 0.0
        latest_series_item = None
        iter = QTreeWidgetItemIterator(self)
        while iter.value():
            item = iter.value()
            if item.text(3):
                timestamp = time.mktime(time.strptime(item.text(3), "%Y-%m-%d %H:%M:%S"))
                if  timestamp > latest_time:
                    latest_time = timestamp
                    latest_series_item = item
            iter.__iadd__(1)
        self.series_selected_signal.emit(latest_series_item,
                                         self.get_series_files(latest_series_item))

    def send_latest_modified_series(self):
        '''将最后编辑的序列发送给外部窗口'''
        latest_time = 0.0
        latest_series_item = None
        iter = QTreeWidgetItemIterator(self)
        while iter.value():
            item = iter.value()
            if item.text(4):
                timestamp = time.mktime(time.strptime(item.text(4), "%Y-%m-%d %H:%M:%S"))
                if timestamp > latest_time:
                    latest_time = timestamp
                    latest_series_item = item
            iter.__iadd__(1)
        print(latest_time, latest_series_item, self.get_series_files(latest_series_item))
        self.series_selected_signal.emit(latest_series_item,
                                         self.get_series_files(latest_series_item))

    def save_item_states_and_modified_time(self):
        '''保存视图中节点的被标记状态到数据库中元素的被标记状态'''
        # warning 大型数据库保存的时间代价?
        iter = QTreeWidgetItemIterator(self)
        while iter.value():
            item = iter.value()
            if self.SERIES_MARK in item.text(0):
                element = self.item2element(item)
                element.attrib['annotated'] = str(item.checkState(0))
                if item.text(4):
                    element.attrib['modified_timestamp'] = str(time.mktime(time.strptime(item.text(4), "%Y-%m-%d %H:%M:%S")))
            iter.__iadd__(1)
        self.dicom_tree.save(self.database)

    def build_tree_recursively(self, tree_widget_item: QTreeWidgetItem, dicom_tree_element: Element):
        '''
        将DicomTree中的内容显示到DatabaseWidget
        这是定义DatabaseWidget的核心方法
            因为DatabaseWidget本质上是显示DicomTree内容的容器,提取和显示哪些属性就决定了DatabaseWidget的定义
        '''
        if dicom_tree_element.tag == 'series':
            return
        else:
            for child_element in list(dicom_tree_element):
                text_list = []
                # 提取DicomTree element中的信息构建text_list用于显示(或默认隐藏,条件显示)
                '''
                text字段内容如下,除描述信息外,默认隐藏
                    text(0) 描述信息,帮助用户查找和记忆
                    text(1) uid 能够将当前节点唯一对应到DicomTree中元素的uid,默认不显示,帮助程序从view映射到model
                    text(2) 路径
                    text(3) 导入时间 
                    text(4) 最后编辑时间
                # 
                '''
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
                    modified_timestamp = ''
                    if child_element.attrib['modified_timestamp']:
                        modified_timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(float(child_element.attrib['modified_timestamp'])))
                    text_list = [self.SERIES_MARK + child_element.attrib['number'] + ': ' + child_element.attrib['description'],
                                 child_element.attrib['uid'],
                                 '',
                                 time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(float(child_element.attrib['imported_timestamp']))),
                                 modified_timestamp]
                    # 对于seires，如果其中instance都来自同一目录，显示目录路径为其文件路径
                    dir = ''
                    for instance in list(child_element):
                        if dir and dir != osp.dirname(instance.attrib['path']):
                            print('前后路径', dir, osp.dirname(instance.attrib['path']))
                            break
                        dir = osp.dirname(instance.attrib['path'])
                    else:
                        text_list[2] = dir

                # 构建TreeWidget item
                child_item = QTreeWidgetItem(tree_widget_item)
                # insight: 用默认flags和需要的flag按位异或，就能使需要的flag翻转
                # 其它级别的item : 自动三态,不可手动标记
                child_item.setFlags(child_item.flags() ^ Qt.ItemIsAutoTristate)
                # series级别的item : 可以手动进行三态标记,并且从DicomTree中读取设置状态
                if child_element.tag == 'series' and osp.exists(text_list[2]):
                    child_item.setCheckState(0, int(child_element.attrib['annotated']))

                for i in range(len(text_list)):
                    child_item.setText(i, text_list[i])

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
        if self.SERIES_MARK in self.currentItem().text(0):
            self.series_selected_signal.emit(self.currentItem(), self.get_series_files(self.currentItem()))

    def get_series_files(self, item: QTreeWidgetItem) -> List[str]:
        series_element = self.item2element(item)
        files = [instance.attrib['path'] for instance in list(series_element)]
        return files

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

        return [patient_id, study_uid, series_uid]

    def get_item_from_top_down_uid(self, uids: List[str]) -> QTreeWidgetItem:
        '''获取一个top-down uid列表对应的节点'''
        result_item = None
        if uids:
            patient_id = uids.pop(0)
            patient_items = [self.topLevelItem(0).child(i) for i in range(self.topLevelItem(0).childCount())]
            for patient_item in patient_items:
                if patient_id == patient_item.text(1):
                    result_item = patient_item
                    break
            if uids:
                study_uid = uids.pop(0)
                study_items = [result_item.child(i) for i in
                                 range(result_item.childCount())]
                for study_item in study_items:
                    if study_uid == study_item.text(1):
                        result_item = study_item
                        break
                if uids:
                    series_uid = uids.pop(0)
                    series_items = [result_item.child(i) for i in
                                   range(result_item.childCount())]
                    for series_item in series_items:
                        if series_uid == series_item.text(1):
                            result_item = series_item
                            break
        return result_item

    def item2element(self, item: QTreeWidgetItem) -> Element:
        '''
        获取一个节点在DicomTree中对应的Element
        '''
        return self.dicom_tree.get_element_from_top_down_uid(self.get_top_down_uid(item))

if __name__ == '__main__':
    import sys

    app = QApplication(sys.argv)
    window = DatabaseWidget()
    window.show()
    sys.exit(app.exec_())





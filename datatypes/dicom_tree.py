import pydicom
import os
import os.path as osp
from xml.etree.ElementTree import ElementTree,Element

import time

from typing import Tuple, List, Dict, Set

def digit000(digits: str) -> str:
    if len(digits) <= 3:
        return '0' * (3 - len(digits)) + digits

class DicomTree(ElementTree):
    '''实现三级dicom文件信息树状存储的数据类,从xml ElementTree继承'''

    NOT_ANNOTATED, SYSTEM_DEFINED_ANNOTATED, USER_DEFINED_ANNOTATED = '0', '1', '2'

    def __init__(self):
        super(DicomTree, self).__init__()

    @staticmethod
    def load(xml_path: str):
        dicom_tree = DicomTree()
        dicom_tree.parse(xml_path)
        return dicom_tree

    def save(self, fp: str):
        if not fp.endswith('.xml'):
            return
        self.write(fp, encoding='utf-8',xml_declaration=True)

    @property
    def patients(self) -> Set[str]:
        '''获得Dicom树上所有不同的patient id'''
        patient_id_list = [patient.get('id') for patient in  self._root.iter('patient')]
        return set(patient_id_list)

    @property
    def studies(self) -> Set[str]:
        '''获得Dicom树上所有不同的study uid'''
        study_uid_list = [study.get('uid') for study in  self._root.iter('study')]
        return set(study_uid_list)

    @staticmethod
    def load_from_dir(dir: str, name: str):
        '''递归遍历指定路径，收集其中所有dicom文件建立Dicom树'''
        dicom_tree = DicomTree()
        dicom_tree._root = Element('database')
        dicom_tree._root.attrib = {'name': name}
        # 递归遍历指定目录下所有的文件，读取所有dicom文件的元信息，增加到Dicom树
        for root, dirs, files in os.walk(dir):
            for file in files:
                if file.lower().endswith('.dcm'):
                    dicom_tree.add_file(osp.join(root, file))
        return dicom_tree

    @staticmethod
    def get_necessary_meatadata(dicom_object):
        '''读取进行添加和建库操作需要的元数据'''
        # 患者名在pydicom中被读取为PersonName3对象，不能直接作为字符串被序列化
        name_object = dicom_object[0x0010, 0x0010].value
        metadata_dict = {
            'Patient ID': dicom_object[0x0010, 0x0020].value,  # 患者的序号
            'Patient Name': name_object.family_name + name_object.given_name,  # 患者名字
            'Study UID': dicom_object[0x0020, 0x000D].value,  # study的唯一标识符
            'Study ID': dicom_object[0x0020, 0x0010].value,  # study的序号
            'Study Date': dicom_object[0x0008, 0x0020].value,  # study的日期
            'Study Time': dicom_object[0x0008, 0x0030].value,  # study的时间
            'Series UID': dicom_object[0x0020, 0x000E].value,  # series的唯一标识符
            'Series Number': digit000(str(dicom_object[0x0020, 0x0011].value)),  # series的序号
            'Series Description': dicom_object[0x0008, 0x103E].value,  # series的描述文本
            'Instance UID': dicom_object[0x0008, 0x0018].value,  # instance的唯一标识符
            'Instance Number': digit000(str(dicom_object[0x0020, 0x0013].value)),  # instance的序号
        }
        return metadata_dict

    def add_file(self, fp: str) -> None:
        '''
        增加文件到Dicom树
        这是定义Dicom树的核心方法
            因为Dicom树本质上只是具有特定Element和Attribute的xml树,提取和维护哪些属性就决定了DicomTree的定义
        '''
        # TEST
        print(fp)
        '''将.dcm文件索引加入Dicom树'''
        if not fp.endswith('.dcm'):
            return

        dicom_object = pydicom.dcmread(fp)

        metadata_dict = DicomTree.get_necessary_meatadata(dicom_object)

        # 逐级检查标识符，若无则创建，若有则添加到其上
        # 检查是否已有此患者
        patient_id_list = [patient.get('id') for patient in list(self._root)]
        patient_id = metadata_dict['Patient ID']
        if patient_id not in patient_id_list:
            # 构建新的patient元素
            new_patient = Element('patient')
            new_patient.attrib = {
                'id': metadata_dict['Patient ID'],
                'name': metadata_dict['Patient Name']
            }
            # 根据patient id进行排序，将新的patient元素插入合适的位置
            patient_id_list.append(metadata_dict['Patient ID'])
            index = sorted(patient_id_list).index(metadata_dict['Patient ID'])
            self._root.insert(index, new_patient)
            current_patient = new_patient
        else:
            current_patient = list(self._root)[patient_id_list.index(patient_id)]

        # 检查是否已有此study，执行操作同上
        study_uid_list = [study.get('uid') for study in current_patient.findall('study')]
        study_id_list = [study.get('id') for study in current_patient.findall('study')]
        study_uid = metadata_dict['Study UID']
        if study_uid not in study_uid_list:
            new_study = Element('study')
            new_study.attrib = {
                'uid': metadata_dict['Study UID'],
                'id': metadata_dict['Study ID'],
                'date': metadata_dict['Study Date'],
                'time': metadata_dict['Study Time']
            }
            study_id_list.append(metadata_dict['Study ID'])
            index = sorted(study_id_list).index(metadata_dict['Study ID'])
            current_patient.insert(index, new_study)
            current_study = new_study
        else:
            current_study = list(current_patient)[study_uid_list.index(study_uid)]

        # 检查是否已有此series，执行操作同上
        series_uid_list = [series.get('uid') for series in current_study.findall('series')]
        series_number_list = [series.get('number') for series in current_study.findall('series')]
        series_uid = metadata_dict['Series UID']
        if  series_uid not in series_uid_list:
            new_series = Element('series')
            new_series.attrib = {
                'uid': metadata_dict['Series UID'],
                'number': metadata_dict['Series Number'],
                'description': metadata_dict['Series Description'],
                'annotated' : self.NOT_ANNOTATED
            }
            series_number_list.append(metadata_dict['Series Number'])
            index = sorted(series_number_list).index(metadata_dict['Series Number'])
            current_study.insert(index, new_series)
            current_series = new_series
        else:
            current_series = list(current_study)[series_uid_list.index(series_uid)]
        # 根据标记文件的存在性,在series级上标记序列的被标记状况
        if osp.exists(fp.replace('.dcm', '.pkl')):
            current_series.attrib.update({'annotated' : self.SYSTEM_DEFINED_ANNOTATED})

        # 检查是否已有此instance
        instance_uid_list = [instance.get('uid') for instance in current_series.findall('instance')]
        instance_number_list = [instance.get('number') for instance in
                                current_series.findall('instance')]
        instance_uid = metadata_dict['Instance UID']

        if  instance_uid not in instance_uid_list:
            new_instance = Element('instance')
            new_instance.attrib = {
                'uid': metadata_dict['Instance UID'],
                'number': metadata_dict['Instance Number'],
                'path': fp
            }
            # 根据instance number进行排序
            instance_number_list.append(metadata_dict['Instance Number'])
            index = sorted(instance_number_list).index(metadata_dict['Instance Number'])
            current_series.insert(index, new_instance)

    def add_files(self, fps: list) -> None:
        '''将若干文件加入Dicom树，只有dcm文件会被添加'''
        for fp in fps:
            self.add_file(fp)

    def search_by_top_down_uid(self, uid: List[str]) -> Element:
        '''
        根据从前往后，自顶向下的uid列表查找element,返回element
        uid列表形式如同[patientID studyUID seriesUID instanceUID],根据查找的级别后面的ID可以缺省
        '''
        result_element = None
        if uid:
            patient_id = uid.pop(0)
            for patient in self.getroot().findall('patient'):
                if patient.attrib['id'] == patient_id:
                    result_element = patient
                    break
            if uid and result_element:
                study_uid = uid.pop(0)
                for study in result_element.findall('study'):
                    if study.attrib['uid'] == study_uid:
                        result_element = study
                        break
                if uid and result_element:
                    series_uid = uid.pop(0)
                    for series in result_element.findall('series'):
                        if series.attrib['uid'] == series_uid:
                            result_element = series
                            break
                    if uid and result_element:
                        instance_uid = uid.pop(0)
                        for instance in result_element.findall('instance'):
                            if instance.attrib['uid'] == instance_uid:
                                result_element = instance
                                break
        return result_element

if __name__ == '__main__':

    database_dir = r'Z:\SYSU-LUNG\炎性假瘤 CT 良性\10044893\动脉期'
    SYSU_tree = DicomTree()
    SYSU_tree._root = Element('database')
    SYSU_tree._root.attrib = {'name': 'default'}
    SYSU_tree.add_file(r'Z:\SYSU-LUNG\炎性假瘤 CT 良性\10044893\实质期\ser009img00001.dcm')
    SYSU_tree.add_file(r'Z:\SYSU-LUNG\炎性假瘤 CT 良性\10044893\实质期\ser009img00002.dcm')
    # SYSU_tree.add_files([r'Z:\SYSU-LUNG\炎性假瘤 CT 良性\10044893\实质期\ser009img00001.dcm', r'Z:\SYSU-LUNG\炎性假瘤 CT 良性\10044893\实质期\ser009img00002.dcm'])
    SYSU_tree.save('default.xml')

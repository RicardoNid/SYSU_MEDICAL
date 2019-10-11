import pydicom
import os
import os.path as osp
from xml.etree.ElementTree import ElementTree,Element

from typing import Tuple, List, Dict, Set

def digit000(digits: str) -> str:
    if len(digits) <= 3:
        return '0' * (3 - len(digits)) + digits

class DicomTree(ElementTree):
    '''实现三级dicom文件信息树状存储的数据类,从xml ElementTree继承'''
    def __init__(self):
        super(DicomTree, self).__init__()

    @staticmethod
    def load(xml_path: str):
        dicom_tree = DicomTree()
        dicom_tree.parse(xml_path)
        return dicom_tree

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
                    dicom_object = pydicom.dcmread(osp.join(root, file))
                    # 读取需要的元数据
                    # 患者名在pydicom中被读取为PersonName3对象，不能直接作为字符串被序列化
                    name_object = dicom_object[0x0010, 0x0010].value
                    metadata_dict = {
                        'Patient ID': dicom_object[0x0010, 0x0020].value,  # 患者的序号
                        'Patient Name': name_object.family_name + name_object.given_name,  # 患者名字
                        'Study UID': dicom_object[0x0020, 0x000D].value, #study的唯一标识符
                        'Study ID': dicom_object[0x0020, 0x0010].value, # study的序号
                        'Study Date': dicom_object[0x0008, 0x0020].value, # study的日期
                        'Study Time': dicom_object[0x0008, 0x0030].value, # study的时间
                        'Series UID': dicom_object[0x0020, 0x000E].value,  # series的唯一标识符
                        'Series Number': digit000(str(dicom_object[0x0020, 0x0011].value)), # series的序号
                        'Series Description': dicom_object[0x0008, 0x103E].value, # series的描述文本
                        'Instance UID': dicom_object[0x0008, 0x0018].value, # instance的唯一标识符
                        'Instance Number': digit000(str(dicom_object[0x0020, 0x0013].value)), # instance的序号
                    }
                    # 逐级检查标识符，若无则创建，若有则添加到其上
                    # 检查是否已有此患者
                    patient_id_list = [patient.get('id') for patient in dicom_tree._root.findall('patient')]
                    if metadata_dict['Patient ID'] not in patient_id_list:
                        new_patient = Element('patient')
                        new_patient.attrib = {
                            'id': metadata_dict['Patient ID'],
                            'name': metadata_dict['Patient Name']
                        }
                        # 根据patient id进行排序
                        patient_id_list.append(metadata_dict['Patient ID'])
                        index = sorted(patient_id_list).index(metadata_dict['Patient ID'])
                        # question: index? 还是+1或-1?
                        dicom_tree._root.insert(index, new_patient)
                        current_patient = new_patient
                    else:
                        for patient in dicom_tree._root.findall('patient'):
                            if patient.attrib['id'] == metadata_dict['Patient ID']:
                                current_patient = patient
                                break
                    # 检查是否已有此study
                    study_uid_list = [study.get('uid') for study in current_patient.findall('study')]
                    study_id_list = [study.get('id') for study in current_patient.findall('study')]
                    if metadata_dict['Study UID'] not in study_uid_list:
                        new_study = Element('study')
                        new_study.attrib = {
                            'uid': metadata_dict['Study UID'],
                            'id': metadata_dict['Study ID'],
                            'date': metadata_dict['Study Date'],
                            'time': metadata_dict['Study Time']
                        }
                        # 根据study id进行排序
                        study_id_list.append(metadata_dict['Study ID'])
                        index = sorted(study_id_list).index(metadata_dict['Study ID'])
                        current_patient.insert(index, new_study)
                        current_study = new_study
                    else:
                        for study in current_patient.findall('study'):
                            if study.attrib['uid'] == metadata_dict['Study UID']:
                                current_study = study
                                break
                    # 检查是否已有此series
                    series_uid_list = [series.get('uid') for series in current_study.findall('series')]
                    series_number_list = [series.get('number') for series in current_study.findall('series')]
                    if metadata_dict['Series UID'] not in series_uid_list:
                        new_series = Element('series')
                        new_series.attrib = {
                            'uid': metadata_dict['Series UID'],
                            'number': metadata_dict['Series Number'],
                            'description': metadata_dict['Series Description']
                        }
                        # 根据series number进行排序
                        series_number_list.append(metadata_dict['Series Number'])
                        index = sorted(series_number_list).index(metadata_dict['Series Number'])
                        current_study.insert(index, new_series)
                        current_series = new_series
                    else:
                        for series in current_patient.findall('series'):
                            if series.attrib['uid'] == metadata_dict['Series UID']:
                                current_series = series
                                break
                    # 检查是否已有此instance
                    instance_uid_list = [instance.get('uid') for instance in current_series.findall('instance')]
                    instance_number_list = [instance.get('number') for instance in current_series.findall('instance')]
                    if metadata_dict['Instance UID'] not in instance_uid_list:
                        new_instance = Element('instance')
                        new_instance.attrib = {
                            'uid': metadata_dict['Instance UID'],
                            'number': metadata_dict['Instance Number'],
                            'path': osp.join(root, file)
                        }
                        # 根据instance number进行排序
                        instance_number_list.append(metadata_dict['Instance Number'])
                        index = sorted(instance_number_list).index(metadata_dict['Instance Number'])
                        current_series.insert(index, new_instance)
        return dicom_tree

if __name__ == '__main__':

    database_dir = r'Y:\MRI\demo\10149857'
    tree = DicomTree()
    mri_tree = DicomTree.load_from_dir(database_dir, 'MRI数据库')
    mri_tree.write('example.xml', encoding='utf-8',xml_declaration=True)


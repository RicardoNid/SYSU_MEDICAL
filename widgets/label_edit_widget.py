from common_import import *

from ui_LabelEditWidget import Ui_LabelEditWidget
from ui_LabelEditDialog import Ui_LabelEditDialog

from datatypes import LabelStruct

class LabelEditWidget(QListWidget, Ui_LabelEditWidget):

    apply_label_signal = pyqtSignal(object)

    def __init__(self):
        super(LabelEditWidget, self).__init__()
        self.setupUi(self)
        self.init_enum()
        self.init_content()

        self.apply_button.clicked.connect(self.apply_button_slot)
        self.lobulation_combobox.currentTextChanged.connect(self.change_segmentation_item)
        self.reset_button.clicked.connect(self.reset_button_slot)

    def init_enum(self):
        '''初始化枚举量'''
        self.mali_enum = {
            'malignant': self.malignant_button,
            'benign': self.benign_button,
            'unknown': self.malignancy_unknown_button,
        }
        self.soli_enum = {
            'solid': self.solid_button,
            'ground glass': self.ground_glass_button,
            'unknown': self.solidity_unknown_button,
        }

    def init_content(self):
        self.default_dict = {
            'malignancy': 'unknown', # 良恶
            'solidity': 'unknown', # 实性
            'lobulation': '？', # 分叶
            'segmentation': '？', # 分段
            'signs': '无', # 影像学征象
            'comment': '', # 备注
        }
        self.label = LabelStruct(**self.default_dict)
        self.refresh()

    def refresh(self):
        # 根据标签刷新控件状态
        self.mali_enum[self.label.malignancy].setChecked(True)
        self.soli_enum[self.label.solidity].setChecked(True)
        self.lobulation_combobox.setCurrentText(self.label.lobulation)
        self.segmentation_comgbobox.setCurrentText(self.label.segmentation)
        self.sign_combobox.setCurrentText(self.label.signs)
        self.comment_edit.setText(self.label.comment)

    def apply_button_slot(self):
        '''应用对标签的的编辑：根据控件状态输出标签'''
        output_dict = {}
        if self.benign_button.isChecked():
            output_dict.update({'malignancy': 'benign'})
        elif self.malignant_button.isChecked():
            output_dict.update({'malignancy': 'malignant'})
        else:
            output_dict.update({'malignancy': 'unknown'})

        if self.solid_button.isChecked():
            output_dict.update({'solidity': 'solid'})
        elif self.ground_glass_button.isChecked():
            output_dict.update({'solidity': 'ground glass'})
        else:
            output_dict.update({'solidity': 'unknown'})

        output_dict['lobulation'] = self.lobulation_combobox.currentText()
        output_dict['segmentation'] = self.segmentation_comgbobox.currentText()
        output_dict['signs'] = self.sign_combobox.currentText()
        output_dict['comment'] = self.comment_edit.toPlainText()

        output_label_struct = LabelStruct(**output_dict)
        self.apply_label_signal.emit(output_label_struct)

    def change_segmentation_item(self):
        lobulation_segmentation_dict = {
            '？': ['？'],
            '右肺上叶': ['尖段','后段','前段'],
            '右肺中叶': ['外侧段','内侧段'],
            '右肺下叶': ['背段','内基底段','前基底段','外基底段','后基底段'],
            '左肺上叶': ['尖后段','前段','上舌段','下舌段'],
            '左肺下叶': ['背段','前基底段','外基底段','后基底段'],
        }
        self.segmentation_comgbobox.clear()
        for segmentation in lobulation_segmentation_dict[self.lobulation_combobox.currentText()]:
            self.segmentation_comgbobox.addItem(segmentation)

    def reset_button_slot(self):
        '''重置对标签的编辑：控件回到初始状态'''
        self.label = LabelStruct(**self.default_dict)
        self.refresh()

class LabelEditDialog(QDialog, Ui_LabelEditDialog):
    def __init__(self):
        super(LabelEditDialog, self).__init__()
        self.setupUi(self)
        self.init_enum()
        self.init_content()

        self.confirm_button.clicked.connect(self.confirm_button_slot)
        self.lobulation_combobox.currentTextChanged.connect(self.change_segmentation_item)

    def init_enum(self):
        '''初始化枚举量'''
        self.mali_enum = {
            'malignant': self.malignant_button,
            'benign': self.benign_button,
            'unknown': self.malignancy_unknown_button,
        }
        self.soli_enum = {
            'solid': self.solid_button,
            'ground glass': self.ground_glass_button,
            'unknown': self.solidity_unknown_button,
        }

    def init_content(self):
        self.default_dict = {
            'malignancy': 'unknown',  # 良恶
            'solidity': 'unknown',  # 实性
            'lobulation': '？',  # 分叶
            'segmentation': '？',  # 分段
            'signs': '无',  # 影像学征象
            'comment': '',  # 备注
        }
        self.label = LabelStruct(**self.default_dict)

        self.malignancy_unknown_button.setChecked(True)
        self.solidity_unknown_button.setChecked(True)
        self.lobulation_combobox.setCurrentText('？')
        self.segmentation_comgbobox.setCurrentText('？')
        self.sign_combobox.setCurrentText('无')

    def confirm_button_slot(self):
        '''应用对标签的的编辑：根据控件状态输出标签'''
        label_dict = {}
        if self.benign_button.isChecked():
            label_dict.update({'malignancy': 'benign'})
        elif self.malignant_button.isChecked():
            label_dict.update({'malignancy': 'malignant'})
        else:
            label_dict.update({'malignancy': 'unknown'})

        if self.solid_button.isChecked():
            label_dict.update({'solidity': 'solid'})
        elif self.ground_glass_button.isChecked():
            label_dict.update({'solidity': 'ground glass'})
        else:
            label_dict.update({'solidity': 'unknown'})

        label_dict['lobulation'] = self.lobulation_combobox.currentText()
        label_dict['segmentation'] = self.segmentation_comgbobox.currentText()
        label_dict['signs'] = self.sign_combobox.currentText()
        label_dict['comment'] = ''

        self.label = LabelStruct(**label_dict)
        self.close()

    def change_segmentation_item(self):
        lobulation_segmentation_dict = {
            '？': ['？'],
            '右肺上叶': ['尖段','后段','前段'],
            '右肺中叶': ['外侧段','内侧段'],
            '右肺下叶': ['背段','内基底段','前基底段','外基底段','后基底段'],
            '左肺上叶': ['尖后段','前段','上舌段','下舌段'],
            '左肺下叶': ['背段','前基底段','外基底段','后基底段'],
        }
        self.segmentation_comgbobox.clear()
        for segmentation in lobulation_segmentation_dict[self.lobulation_combobox.currentText()]:
            self.segmentation_comgbobox.addItem(segmentation)

    # insight: 为自定义输入框设计get方法，而不是通过信号连接
    @staticmethod
    def get_label():
        dialog = LabelEditDialog()
        dialog.setGeometry(QCursor.pos().x(), QCursor.pos().y(), 240, 180)
        dialog.exec_()
        return dialog.label


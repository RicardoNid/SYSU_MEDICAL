from common_import import *
import logger

class LungNoduleLabel():
    '''肺结节标签数据，参照LIDC设计'''
    def __init__(self):
        pass

    @property
    def malignancy(self):
        '''良恶程度'''
        return self._malignancy

    @malignancy.setter
    def malignancy(self, value: str):
        if value not in ['良性', '恶性']:
            return
        else: self._malignancy = value

    @property
    def signs(self):
        return self._malignancy

class LungNoduleLabelWidget(QWidget):
    pass
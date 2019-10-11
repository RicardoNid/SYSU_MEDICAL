from common_import import *

import pydicom
from pydicom.multival import MultiValue
import numpy as np
import PIL.Image, PIL.ImageQt

def get_dicom_info(dicom_path: str):
    dicom_object = pydicom.dcmread(dicom_path)
    dicom_array = dicom_object.pixel_array
    try:
        intercept = dicom_object[0x28, 0x1052].value
        slope = dicom_object[0x28, 0x1053].value
        dicom_array = (dicom_array * slope) + intercept
    except:
        pass

    wl = dicom_object[0x28, 0x1050].value
    if isinstance(wl, MultiValue):
        wl = wl.pop()
    ww = dicom_object[0x28, 0x1051].value
    if isinstance(ww, MultiValue):
        ww = ww.pop()

    return wl, ww, dicom_array

def dicom_array2pixmap(wl: int, ww: int, dicom_array: np.ndarray) -> QPixmap:

    dicom_array = np.minimum(dicom_array, wl + ww / 2)
    dicom_array = np.maximum(dicom_array, wl - ww / 2)
    dicom_array = np.round(((dicom_array - (wl - ww / 2)) * 255 / ww))
    dicom_image = PIL.Image.fromarray(dicom_array)
    dicom_image = dicom_image.convert('L')

    image = PIL.ImageQt.ImageQt(dicom_image)
    pixmap = QPixmap.fromImage(image)
    return pixmap
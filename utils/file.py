import os
import os.path as osp

def get_dicom_files_path_from_dir(dir):
    return [osp.join(dir, file) for file in os.listdir(dir) if file.lower().endswith('.dcm')]
"""Utility script to flatten OASIS-2 directory structure."""
import glob
import os
from argparse import ArgumentParser
from typing import List, Tuple

import nibabel

NIFTI_FILE_EXT = '.nii.gz'


def list_paths(dir_path: str) -> List[Tuple[str, str]]:
    return [(n, os.path.join(dir_path, n)) for n in os.listdir(dir_path)]


def flatten_structure(dataset_path: str, save_container_path: str) -> str:
    os.makedirs(save_container_path, exist_ok=True)

    image_count = 0

    for session_dir_name, session_dir_path in sorted(list_paths(dataset_path), key=lambda t: t[0]):
        session_images_dir_path = os.path.join(session_dir_path, 'RAW')

        for image_path in sorted(glob.glob(os.path.join(session_images_dir_path, 'mpr-*.nifti.img'))):
            scan_name = os.path.basename(image_path).split('.')[0]
            save_name = session_dir_name + '_' + scan_name

            save_path = os.path.join(save_container_path, save_name + NIFTI_FILE_EXT)

            nibabel.save(nibabel.load(image_path), save_path)
            print('Saved', save_path)
            image_count += 1

    print('\nSuccessfully saved {} images'.format(image_count))
    return save_container_path


if __name__ == '__main__':
    parser = ArgumentParser()

    parser.add_argument('dataset_path', type=str)
    parser.add_argument('output_path', type=str)
    args = parser.parse_args()

    flatten_structure(args.dataset_path, args.output_path)

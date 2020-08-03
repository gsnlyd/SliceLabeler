"""Utility script to flatten OASIS-3 directory structure."""
import glob
import os
import shutil
from argparse import ArgumentParser

NIFTI_FILE_EXT = '.nii.gz'


def flatten_structure(dataset_path: str, output_path: str):
    os.makedirs(output_path, exist_ok=True)
    print('Created {}'.format(output_path))

    image_count = 0
    for sess_dir_name in os.listdir(dataset_path):
        sess_dir_path = os.path.join(dataset_path, sess_dir_name)
        if not os.path.isdir(sess_dir_path):
            continue
        for anat_dir_name in os.listdir(sess_dir_path):
            anat_dir_path = os.path.join(sess_dir_path, anat_dir_name)
            if not os.path.isdir(anat_dir_path):
                continue

            assert anat_dir_name.startswith('anat'), 'Invalid name: {}'.format(anat_dir_name)

            glob_path = os.path.join(anat_dir_path, 'NIFTI', '*' + NIFTI_FILE_EXT)
            image_paths = glob.glob(glob_path)

            for im_path in image_paths:
                save_path = os.path.join(output_path, '{}_{}_{}'.format(sess_dir_name, anat_dir_name,
                                                                        os.path.basename(im_path)))
                assert not os.path.exists(save_path), '{} already exists'.format(save_path)

                shutil.copyfile(im_path, save_path)
                image_count += 1

    print('Successfully saved {} images'.format(image_count))


if __name__ == '__main__':
    parser = ArgumentParser()

    parser.add_argument('dataset_path', type=str)
    parser.add_argument('output_path', type=str)
    args = parser.parse_args()

    flatten_structure(args.dataset_path, args.output_path)

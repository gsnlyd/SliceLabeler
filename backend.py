import csv
import os
import random
from datetime import datetime
from enum import Enum
from io import StringIO
from typing import List, Dict, Tuple, NamedTuple, Optional

import nibabel
import numpy as np
from PIL import Image
from sqlalchemy.orm import Session

from model import LabelSession

DATASETS_PATH = 'data/datasets'
SLICES_PATH = 'static/slices'
COMPARISON_LISTS_PATH = 'comparison_lists'

ALLOWED_IMAGE_EXTENSIONS = [  # TODO: Add more
    'nii.gz'
]

THUMB_CACHE_SIZE = 4
COMPARISON_LIST_CACHE_SIZE = 3


class SliceType(Enum):
    SAGITTAL = 0
    CORONAL = 1
    AXIAL = 2


class Dataset(NamedTuple):
    name: str
    path: str


class DataImage(NamedTuple):
    dataset: Dataset
    name: str
    path: str


class ImageSlice(NamedTuple):
    image_name: str
    slice_index: int
    slice_type: SliceType


def get_datasets() -> List[Dataset]:
    datasets = [Dataset(n, os.path.join(DATASETS_PATH, n)) for n in os.listdir(DATASETS_PATH)]
    return [d for d in datasets if os.path.isdir(d.path)]


def get_dataset(dataset_name: str) -> Optional[Dataset]:
    d_path = os.path.join(DATASETS_PATH, dataset_name)
    if os.path.exists(d_path):
        return Dataset(dataset_name, d_path)
    else:
        return None


def is_image_path(path: str) -> bool:
    # Use .split() because .splitext() splits on the last dot (name.nii.gz becomes [name.nii, .gz])
    return os.path.isdir(path) or os.path.basename(path).split(os.extsep, 1)[1] in ALLOWED_IMAGE_EXTENSIONS


def get_images(dataset: Dataset) -> List[DataImage]:
    paths = [os.path.join(dataset.path, n) for n in os.listdir(dataset.path)]
    paths = [p for p in paths if is_image_path(p)]

    return [DataImage(dataset, os.path.basename(p), p) for p in sorted(paths)]


def get_image(dataset: Dataset, image_name: str) -> DataImage:
    image_path = os.path.join(dataset.path, image_name)
    assert os.path.exists(image_path), 'Image {} does not exist'.format(image_path)
    return DataImage(dataset, image_name, image_path)


def get_image_by_index(dataset: Dataset, image_index: int) -> Tuple[Optional[DataImage], int]:
    """
    Get an image by its index within its dataset (dataset images are sorted by name).

    :param dataset: The dataset.
    :param image_index: The index of the image.
    :return: A tuple containing the image (or None if the index is out of bounds) and the length of the dataset.
    """
    images = get_images(dataset)
    if 0 <= image_index < len(images):
        return images[image_index], len(images)
    else:
        return None, len(images)


thumb_cache = {}


def __load_cached_image(image: DataImage):
    cache_key = image.dataset.name + image.name
    if cache_key not in thumb_cache:
        thumb_cache[cache_key] = nibabel.as_closest_canonical(nibabel.load(image.path))

        while len(thumb_cache) > THUMB_CACHE_SIZE:
            thumb_cache.pop(list(thumb_cache.keys())[0])

    return thumb_cache[cache_key]


def get_slice(d_img: DataImage, slice_index: int, slice_type: SliceType,
              intensity_min: int, intensity_max: int) -> Image.Image:
    data = __load_cached_image(d_img).get_fdata()

    if slice_type == SliceType.SAGITTAL:
        slice_data = data[slice_index, :, :]
    elif slice_type == SliceType.CORONAL:
        slice_data = data[:, slice_index, :]
    else:  # AXIAL
        slice_data = data[:, :, slice_index]

    if len(slice_data.shape) > 2:
        slice_data = slice_data.squeeze(axis=2)
    slice_data = np.clip(slice_data, intensity_min, intensity_max)
    slice_data = ((slice_data / intensity_max) * 255).astype('uint8')
    slice_data = np.flip(slice_data.T, axis=0)
    return Image.fromarray(slice_data)


def get_image_info(d_img: DataImage) -> Tuple[Tuple[int, int, int], int]:
    """
    Gets info for an image.

    :param d_img: Image to get info from.
    :return: A tuple containing image dimensions (Saggital, Coronal, Axial) and the maximum value of the image.
    """
    data = __load_cached_image(d_img).get_fdata()
    shape = data.shape
    return (shape[0], shape[1], shape[2]), int(np.max(data))


def get_dataset_label_sessions(session: Session, dataset: Dataset) -> List[LabelSession]:
    return session.query(LabelSession).filter(LabelSession.dataset == dataset.name) \
        .order_by(LabelSession.date_created).all()


def export_labels(session: Session, label_session: LabelSession):
    """Exports all labels for the given label_session to a StringIO in csv format."""
    rows = []

    if label_session.session_type == LabelSessionType.CATEGORICAL_VOLUME.value:
        dataset = get_dataset(label_session.dataset)
        assert dataset is not None

        labels = get_session_labels_categorical(session, label_session.id, get_images(dataset), descending=False)

        header = ('image_index', 'image_name', 'label_value', 'date_labeled', 'interaction_ms')
        for im_i, im_labels in enumerate(labels.values()):
            for la in im_labels:
                rows.append((
                    im_i,
                    la.image_name,
                    la.label_value,
                    str(la.date_labeled),
                    la.interaction_ms
                ))
    elif label_session.session_type == LabelSessionType.CATEGORICAL_SLICE.value:
        slices = get_comparison_slices(label_session.comparison_list_name)
        labels = get_slice_labels(session, label_session.id, slices, descending=False)
        header = ('slice', 'image_name', 'slice_index', 'slice_type', 'label_value', 'date_labeled', 'interaction_ms')
        for image_slice_i, (sl, sl_labels) in enumerate(zip(slices, labels)):
            for la in sl_labels:
                rows.append((
                    image_slice_i,
                    sl.image_name,
                    sl.slice_index,
                    sl.slice_type.name,
                    la.label_value,
                    str(la.date_labeled),
                    la.interaction_ms
                ))
    else:  # COMPARISON_SLICE
        comparison_list = load_comparison_list(label_session.comparison_list_name)
        labels = get_session_labels_comparison(session, label_session.id, comparison_list, descending=False)

        header = ('comparison_index', 'image_1', 'slice_1', 'orientation_1',
                  'image_2', 'slice_2', 'orientation_2', 'label_value', 'date_labeled', 'time_taken_ms')
        for co_labels in labels:
            for la in co_labels:
                rows.append((
                    la.comparison_index,
                    la.image_1_name,
                    la.slice_1_index,
                    la.slice_1_type,
                    la.image_2_name,
                    la.slice_2_index,
                    la.slice_2_type,
                    la.label_value,
                    str(la.date_labeled),
                    la.time_taken_ms
                ))

    sio = StringIO()

    writer = csv.writer(sio)
    writer.writerow(header)
    for r in rows:
        writer.writerow(r)

    return sio

import os
from enum import Enum
from typing import List, Tuple, NamedTuple, Optional

import nibabel
import numpy as np
from PIL import Image

DATASETS_PATH = 'data/datasets'
SLICES_PATH = 'static/slices'
COMPARISON_LISTS_PATH = 'comparison_lists'

ALLOWED_IMAGE_EXTENSIONS = [  # TODO: Add more
    'nii.gz',
    'nii'
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

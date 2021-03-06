import os
from typing import List, NamedTuple, Dict

import backend
import sampling
from model import LabelSession

THUMBS_PATH = os.path.join('static', 'thumbnails')
THUMB_EXTENSION = '.jpg'
THUMB_MAX_PERCENTILE = 99


class ThumbData(NamedTuple):
    path: str
    exists: bool


def get_dataset_thumbnails_path(dataset: backend.Dataset) -> str:
    return os.path.join(THUMBS_PATH, dataset.name)


def get_thumbnail_name(image_slice: backend.ImageSlice) -> str:
    return backend.slice_name(image_slice) + THUMB_EXTENSION


def get_thumbnails(label_session: LabelSession) -> Dict[backend.ImageSlice, ThumbData]:
    d_path = get_dataset_thumbnails_path(backend.get_dataset(label_session.dataset))
    slices = sampling.get_slices_from_session(label_session)

    thumbs_data = {}
    for sl in slices:
        path = os.path.join(d_path, get_thumbnail_name(sl))
        thumbs_data[sl] = ThumbData(path, os.path.exists(path))
    return thumbs_data


def create_thumbnails(label_session: LabelSession):
    dataset = backend.get_dataset(label_session.dataset)
    slices = sampling.get_slices_from_session(label_session)

    dataset_thumbs_path = get_dataset_thumbnails_path(dataset)
    os.makedirs(dataset_thumbs_path, exist_ok=True)

    created = 0
    for sl in slices:
        d_img = backend.get_image(dataset, sl.image_name)
        slice_thumb_path = os.path.join(dataset_thumbs_path, get_thumbnail_name(sl))
        if not os.path.exists(slice_thumb_path):
            img = backend.get_slice(d_img, sl.slice_index, sl.slice_type, 0, None, THUMB_MAX_PERCENTILE)
            img.save(slice_thumb_path)
            created += 1

    print('Created {} thumbnails for session {} (skipped {}, total {})'.format(
        created, label_session.session_name, len(slices) - created, len(slices)
    ))

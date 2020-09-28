import os
from typing import List

import backend
import sampling
from model import LabelSession

THUMBS_PATH = os.path.join('static', 'thumbnails')
THUMB_EXTENSION = '.jpg'


def get_session_thumbnails_dir_path(label_session: LabelSession) -> str:
    return os.path.join(THUMBS_PATH, 'session-{}'.format(label_session.id))


def get_thumbnail_name(image_slice: backend.ImageSlice) -> str:
    return backend.slice_name(image_slice) + THUMB_EXTENSION


def create_thumbnails(label_session: LabelSession):
    dataset = backend.get_dataset(label_session.dataset)
    slices = sampling.get_slices_from_session(label_session)

    session_thumbs_dir_path = get_session_thumbnails_dir_path(label_session)
    os.makedirs(session_thumbs_dir_path, exist_ok=True)

    for sl in slices:
        d_img = backend.get_image(dataset, sl.image_name)
        slice_thumb_path = os.path.join(session_thumbs_dir_path, backend.slice_name(sl) + '.jpg')
        backend.get_slice(d_img, sl.slice_index, sl.slice_type, 0, None).save(slice_thumb_path)
    print('Created {} thumbnails for session {}'.format(len(slices), label_session.session_name))


def has_thumbnails(label_session: LabelSession) -> bool:
    return os.path.exists(get_session_thumbnails_dir_path(label_session))

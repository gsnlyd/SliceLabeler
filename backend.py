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

from model import ImageLabel, LabelSession, ComparisonLabel

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


class ComparisonSlice(NamedTuple):
    image_name: str
    slice_index: int
    slice_type: SliceType


ComparisonList = List[Tuple[ComparisonSlice, ComparisonSlice]]


def create_comparison_list(dataset: Dataset, slice_type: SliceType, image_count: int, slice_count: int,
                           comparison_count: int, min_slice_percent: int, max_slice_percent: int) -> str:
    """
    Creates a comparison list: a csv list of image slice comparisons which can be shared for reproducibility.

    :param dataset: Dataset from which to choose slices.
    :param slice_type: Slice type to use for all slices.
    :param image_count: Number of images from which to choose slices (sampled randomly without replacement).
    :param slice_count: Number of slices to use (sampled randomly with replacement).
    :param comparison_count: Number of comparisons to generate (sampled randomly from slices with replacement).
    :param min_slice_percent: Lower threshold for slices as a percentage (0-99).
    :param max_slice_percent: Upper threshold for slices as a percentage (1-100).
    :return: File name of the newly generated comparison list.
    """
    os.makedirs(COMPARISON_LISTS_PATH, exist_ok=True)

    images = random.sample(get_images(dataset), image_count)
    slices: List[Tuple[str, int]] = []

    for i in range(slice_count):
        im: DataImage = random.choice(images)
        vol = nibabel.load(im.path)

        # Correct for orientation of volume without loading image data
        orientations = [int(v[0]) for v in nibabel.io_orientation(vol.affine)]
        dim = orientations.index(slice_type.value)
        im_slice_max = vol.header.get_data_shape()[dim]

        slice_min = int(im_slice_max * (min_slice_percent / 100))
        slice_max = int(im_slice_max * (max_slice_percent / 100))

        if slice_min == slice_max:
            sl = slice_max
        else:
            sl = random.randrange(slice_min, slice_max)
        slices.append((im.name, sl))

    comparisons: ComparisonList = []

    for i in range(comparison_count):
        sl = random.choice(slices)
        other_sl = random.choice(slices)
        while other_sl == sl:  # Prevent comparison with self
            other_sl = random.choice(slices)
        comparisons.append((
            ComparisonSlice(sl[0], sl[1], slice_type),
            ComparisonSlice(other_sl[0], other_sl[1], slice_type)
        ))

    save_name = dataset.name + '_comparisons_' + datetime.strftime(datetime.now(), '%Y-%m-%d-%H:%M:%S') + '.csv'
    save_path = os.path.join(COMPARISON_LISTS_PATH, save_name)

    with open(save_path, 'w', newline='') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(('image_1', 'slice_1', 'orientation_1', 'image_2', 'slice_2', 'orientation_2'))
        for co in comparisons:
            writer.writerow((
                co[0].image_name, co[0].slice_index, co[0].slice_type.name,
                co[1].image_name, co[1].slice_index, co[1].slice_type.name
            ))
    return os.path.basename(save_path)


def get_comparison_lists(dataset: Dataset) -> List[str]:
    """
    Get all comparison lists for a dataset.

    :param dataset: The dataset.
    :return: The file names of the comparison lists for the given dataset.
    """
    if not os.path.exists(COMPARISON_LISTS_PATH):
        return []

    def is_comparison_list(_n: str) -> bool:
        without_date = '_'.join(_n.split('_')[0:-1])
        return without_date == dataset.name + '_comparisons'

    return sorted([n for n in os.listdir(COMPARISON_LISTS_PATH) if is_comparison_list(n)])


comparison_list_cache: Dict[str, ComparisonList] = {}


def load_comparison_list(name: str) -> ComparisonList:
    """
    Loads a comparison list into memory.

    :param name: The file name of the comparison list.
    :return: A list of tuples containing each ComparisonSlice.
    """
    if name in comparison_list_cache:
        return comparison_list_cache[name]

    comparisons: ComparisonList = []

    load_path = os.path.join(COMPARISON_LISTS_PATH, name)
    assert os.path.exists(load_path)
    with open(load_path, newline='') as csvfile:
        reader = csv.reader(csvfile)
        next(reader)  # Skip header

        for row in reader:
            type_1 = SliceType[row[2]]
            type_2 = SliceType[row[5]]
            assert type_1 is not None and type_2 is not None
            comparisons.append((
                ComparisonSlice(row[0], int(row[1]), type_1),
                ComparisonSlice(row[3], int(row[4]), type_2)
            ))

    comparison_list_cache[name] = comparisons
    while len(comparison_list_cache) > COMPARISON_LIST_CACHE_SIZE:
        comparison_list_cache.pop(list(comparison_list_cache.keys())[0])

    return comparisons


def get_comparison_slices(comparison_list_name: str) -> List[ComparisonSlice]:
    pass


class LabelSessionType(Enum):
    CATEGORICAL_VOLUME = 'categorical'
    CATEGORICAL_SLICE = 'categorical_slice'
    COMPARISON_SLICE = 'comparison'


def create_label_session(session: Session, dataset: Dataset, session_type: LabelSessionType,
                         label_session_name: str, prompt: str,
                         comparison_list_name: str = None, label_values: List[str] = None) -> LabelSession:
    assert comparison_list_name is None or comparison_list_name in get_comparison_lists(dataset)
    if session_type == LabelSessionType.CATEGORICAL_VOLUME or session_type == LabelSessionType.CATEGORICAL_SLICE:
        assert label_values is not None
    if session_type == LabelSessionType.CATEGORICAL_SLICE or session_type == LabelSessionType.COMPARISON_SLICE:
        assert comparison_list_name is not None

    if session_type == LabelSessionType.CATEGORICAL_VOLUME:
        label_session = LabelSession(dataset=dataset.name, session_name=label_session_name,
                                     session_type=session_type.value,
                                     prompt=prompt, date_created=datetime.now(),
                                     categorical_label_values=','.join(label_values))
    elif session_type == LabelSessionType.CATEGORICAL_SLICE:
        label_session = LabelSession(dataset=dataset.name, session_name=label_session_name,
                                     session_type=session_type.value,
                                     prompt=prompt, date_created=datetime.now(),
                                     categorical_label_values=','.join(label_values),
                                     comparison_list_name=comparison_list_name)
    else:  # COMPARISON_SLICE
        label_session = LabelSession(dataset=dataset.name, session_name=label_session_name,
                                     session_type=session_type.value,
                                     prompt=prompt, date_created=datetime.now(),
                                     comparison_list_name=comparison_list_name)

    session.add(label_session)
    session.commit()

    return label_session


def get_label_session_by_id(session: Session, label_session_id: int) -> Optional[LabelSession]:
    return session.query(LabelSession).filter(LabelSession.id == label_session_id).one_or_none()


def get_dataset_label_sessions(session: Session, dataset: Dataset) -> List[LabelSession]:
    return session.query(LabelSession).filter(LabelSession.dataset == dataset.name) \
        .order_by(LabelSession.date_created).all()


def set_categorical_label(session: Session, label_session: LabelSession, image: DataImage,
                          label_value: str, interaction_ms: int):
    assert label_value in label_session.label_values()
    label = ImageLabel(session_id=label_session.id, image_name=image.name, date_labeled=datetime.now(),
                       label_value=label_value, interaction_ms=interaction_ms)
    session.add(label)
    session.commit()


def get_current_categorical_label_value(session: Session, label_session_id: int, image: DataImage) -> Optional[str]:
    label: ImageLabel = session.query(ImageLabel) \
        .filter(ImageLabel.session_id == label_session_id) \
        .filter(ImageLabel.image_name == image.name) \
        .order_by(ImageLabel.date_labeled.desc()) \
        .limit(1) \
        .one_or_none()
    return None if label is None else label.label_value


def get_session_labels_categorical(session: Session, label_session_id: int,
                                   images: List[DataImage], descending: bool = True) -> Dict[str, List[ImageLabel]]:
    """Gets categorical labels for each image sorted by date labeled."""
    order = ImageLabel.date_labeled.desc() if descending else ImageLabel.date_labeled
    all_labels: List[ImageLabel] = session.query(ImageLabel).filter(ImageLabel.session_id == label_session_id) \
        .order_by(order).all()

    labels_per_image: Dict[str, List[ImageLabel]] = {im.name: [] for im in images}
    for im_label in all_labels:
        labels_per_image[im_label.image_name].append(im_label)

    return labels_per_image


COMPARISON_LABEL_VALUES = [
    'First',
    'Second',
    'Neither',
    'Not Sure'
]


def set_comparison_label(session: Session, label_session: LabelSession, comparison_index: int,
                         label_value: str, time_taken_ms: int):
    assert label_value in COMPARISON_LABEL_VALUES
    comparisons = load_comparison_list(label_session.comparison_list_name)
    slice_1, slice_2 = comparisons[comparison_index]

    comparison_label = ComparisonLabel(
        session_id=label_session.id,
        comparison_index=comparison_index,
        image_1_name=slice_1.image_name,
        slice_1_index=slice_1.slice_index,
        slice_1_type=slice_1.slice_type.name,
        image_2_name=slice_2.image_name,
        slice_2_index=slice_2.slice_index,
        slice_2_type=slice_2.slice_type.name,
        label_value=label_value,
        date_labeled=datetime.now(),
        time_taken_ms=time_taken_ms
    )

    session.add(comparison_label)
    session.commit()


def get_current_comparison_label_value(session: Session, label_session_id: int, comparison_index: int) -> str:
    comparison_label: Optional[ComparisonLabel] = session.query(ComparisonLabel) \
        .filter(ComparisonLabel.session_id == label_session_id) \
        .filter(ComparisonLabel.comparison_index == comparison_index) \
        .order_by(ComparisonLabel.date_labeled.desc()) \
        .limit(1) \
        .one_or_none()
    return None if comparison_label is None else comparison_label.label_value


def get_session_labels_comparison(session: Session, label_session_id: int, comparison_list: ComparisonList,
                                  descending: bool = True) -> List[List[ComparisonLabel]]:
    """Gets comparison labels for each comparison sorted by date labeled."""
    order = ComparisonLabel.date_labeled.desc() if descending else ComparisonLabel.date_labeled
    comparison_labels: List[ComparisonLabel] = session.query(ComparisonLabel) \
        .filter(ComparisonLabel.session_id == label_session_id).order_by(order).all()

    labels_per_comparison: List[List[ComparisonLabel]] = [[] for _ in range(len(comparison_list))]
    for co_label in comparison_labels:
        labels_per_comparison[co_label.comparison_index].append(co_label)

    return labels_per_comparison


def export_labels(session: Session, label_session: LabelSession):
    """Exports all labels for the given label_session to a StringIO in csv format."""
    rows = []

    if label_session.session_type == 'categorical':
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
    else:  # Comparison
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

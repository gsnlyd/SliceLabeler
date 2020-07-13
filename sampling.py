import random
from typing import List, Tuple, Optional

import nibabel

import backend
from backend import Dataset, DataImage, ImageSlice, SliceType
from model import LabelSession
from sessions import LabelSessionType


def get_slices_from_session(label_session: LabelSession) -> List[ImageSlice]:
    if label_session.session_type == LabelSessionType.CATEGORICAL_SLICE.name:
        slices = [ImageSlice(el.image_1_name, el.slice_1_index,
                             SliceType[el.slice_1_type]) for el in label_session.elements]
    elif label_session.session_type == LabelSessionType.COMPARISON_SLICE.name:
        comparisons = get_comparisons_from_session(label_session)
        slices = [co[0] for co in comparisons] + [co[1] for co in comparisons]
        slices = set(slices)
        slices = sorted(slices, key=lambda sl: sl.image_name + sl.slice_type.name + str(sl.slice_index))
    else:
        assert False, 'Invalid session type {}'.format(label_session.session_type)

    return slices


def get_comparisons_from_session(label_session: LabelSession) -> List[Tuple[ImageSlice, ImageSlice]]:
    comparisons = []
    for el in label_session.elements:
        comparisons.append((
            ImageSlice(el.image_1_name, el.slice_1_index, SliceType[el.slice_1_type]),
            ImageSlice(el.image_2_name, el.slice_2_index, SliceType[el.slice_2_type])
        ))
    return comparisons


def sample_slices(dataset: Dataset, slice_type: SliceType, image_count: int, slice_count: int,
                  min_slice_percent: int, max_slice_percent: int) -> List[ImageSlice]:
    images = random.sample(backend.get_images(dataset), image_count)
    slices: List[ImageSlice] = []

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
        slices.append(ImageSlice(im.name, sl, slice_type))

    slices = list(set(slices))  # Remove duplicates
    return slices


def sample_comparisons(slices: List[ImageSlice], comparison_count: int,
                       max_comparisons_per_slice: Optional[int]) -> List[Tuple[ImageSlice, ImageSlice]]:
    slices = slices.copy()  # Avoid modifying original list

    slice_comparison_counts = {sl: 0 for sl in slices}
    comparisons: List[Tuple[ImageSlice, ImageSlice]] = []

    def random_slice(avoid: ImageSlice = None) -> ImageSlice:
        sl = random.choice(slices)
        if avoid is not None:
            while sl == avoid:
                sl = random.choice(slices)

        slice_comparison_counts[sl] += 1
        if max_comparisons_per_slice is not None and slice_comparison_counts[sl] >= max_comparisons_per_slice:
            slices.remove(sl)
            assert len(slices) > 0

        return sl

    for i in range(comparison_count):
        sl = random_slice()
        other_sl = random_slice(avoid=sl)  # Prevent comparison with self

        comparisons.append((sl, other_sl))

    return comparisons

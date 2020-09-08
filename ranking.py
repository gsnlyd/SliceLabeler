from typing import List

import sampling
from backend import ImageSlice
from model import LabelSession
from sessions import LabelSessionType


def rank_slices(label_session: LabelSession) -> List[ImageSlice]:
    assert label_session.session_type == LabelSessionType.COMPARISON_SLICE.name

    # TODO: Choose ranking algorithm
    slices = sampling.get_slices_from_session(label_session)
    return slices

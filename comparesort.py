import functools
from typing import Tuple, Optional

from sqlalchemy.orm import Session

import sampling
from backend import ImageSlice
from model import LabelSession, SessionElement


class ComparisonNotFound(Exception):
    pass


def add_next_comparison(session: Session, label_session: LabelSession) -> Optional[SessionElement]:
    comparison_elements = [el for el in label_session.elements if el.image_2_name is not None]
    if len(comparison_elements) > 0 and len(comparison_elements[-1].labels) == 0:
        return comparison_elements[-1]  # There is already a pending comparison

    slices = sampling.get_slices_from_session(label_session)
    comparison_count = len(comparison_elements)

    new_comparison = None

    def compare(sl1: ImageSlice, sl2: ImageSlice):
        for comparison_el in comparison_elements:
            label = comparison_el.labels[-1].label_value
            comparison = sampling.get_comparison_from_element(comparison_el)
            if sl1 == comparison[0] and sl2 == comparison[1]:
                return {'First': 1, 'Second': -1, 'No Difference': 0}[label]
            elif sl1 == comparison[1] and sl2 == comparison[0]:
                return {'First': -1, 'Second': 1, 'No Difference': 0}[label]
        nonlocal new_comparison
        new_comparison = (sl1, sl2)
        raise ComparisonNotFound()

    try:
        sorted(slices, key=functools.cmp_to_key(compare))
        return None
    except ComparisonNotFound:
        assert new_comparison is not None
        new_comparison: Tuple[ImageSlice, ImageSlice]

        comparison_el = SessionElement(
            element_index=comparison_count,
            image_1_name=new_comparison[0].image_name,
            slice_1_index=new_comparison[0].slice_index,
            slice_1_type=new_comparison[0].slice_type.name,
            image_2_name=new_comparison[1].image_name,
            slice_2_index=new_comparison[1].slice_index,
            slice_2_type=new_comparison[1].slice_type.name
        )
        label_session.elements.append(comparison_el)
        session.commit()
        return comparison_el

import json
from datetime import datetime
from enum import Enum, auto
from io import BytesIO, StringIO
from typing import List, Tuple, Optional, Dict

from sqlalchemy.orm import Session
from werkzeug.datastructures import FileStorage

import backend
from backend import SliceType, Dataset, ImageSlice
from model import LabelSession, SessionElement


class LabelSessionType(Enum):
    CATEGORICAL_IMAGE = auto()
    CATEGORICAL_SLICE = auto()
    COMPARISON_SLICE = auto()
    SORT_SLICE = auto()


def get_session_by_id(session: Session, label_session_id: int) -> Optional[LabelSession]:
    return session.query(LabelSession).filter(LabelSession.id == label_session_id).one_or_none()


def get_sessions(session: Session, dataset: Dataset, session_type: LabelSessionType = None) -> List[LabelSession]:
    query = session.query(LabelSession).filter(LabelSession.dataset == dataset.name)
    if session_type is not None:
        query = query.filter(LabelSession.session_type == session_type.name)
    return query.all()


def create_categorical_image_session(session: Session, name: str, prompt: str,
                                     dataset: Dataset, label_values: List[str]):
    images = backend.get_images(dataset)

    label_session = LabelSession(
        dataset=dataset.name,
        session_name=name,
        session_type=LabelSessionType.CATEGORICAL_IMAGE.name,
        prompt=prompt,
        date_created=datetime.now(),
        label_values_str=','.join(label_values),
        element_count=len(images)
    )

    session.add(label_session)

    for i, im in enumerate(images):
        el = SessionElement(
            element_index=i,
            image_1_name=im.name,
            session=label_session
        )
        session.add(el)

    session.commit()


def create_categorical_slice_session(session: Session, name: str, prompt: str,
                                     dataset: Dataset, label_values: List[str], slices: List[ImageSlice]):
    label_session = LabelSession(
        dataset=dataset.name,
        session_name=name,
        session_type=LabelSessionType.CATEGORICAL_SLICE.name,
        prompt=prompt,
        date_created=datetime.now(),
        label_values_str=','.join(label_values),
        element_count=len(slices)
    )

    session.add(label_session)

    for i, sl in enumerate(slices):
        el = SessionElement(
            element_index=i,
            image_1_name=sl.image_name,
            slice_1_index=sl.slice_index,
            slice_1_type=sl.slice_type.name,
            session=label_session
        )
        session.add(el)

    session.commit()


def create_comparison_slice_session(session: Session, name: str, prompt: str,
                                    dataset: Dataset, label_values: List[str],
                                    comparisons: List[Tuple[ImageSlice, ImageSlice]]):
    label_session = LabelSession(
        dataset=dataset.name,
        session_name=name,
        session_type=LabelSessionType.COMPARISON_SLICE.name,
        prompt=prompt,
        date_created=datetime.now(),
        label_values_str=','.join(label_values),
        element_count=len(comparisons)
    )

    session.add(label_session)

    for i, (sl1, sl2) in enumerate(comparisons):
        el = SessionElement(
            element_index=i,
            image_1_name=sl1.image_name,
            slice_1_index=sl1.slice_index,
            slice_1_type=sl1.slice_type.name,
            image_2_name=sl2.image_name,
            slice_2_index=sl2.slice_index,
            slice_2_type=sl2.slice_type.name,
            session=label_session
        )
        session.add(el)

    session.commit()


SORT_LABEL_VALUES_STR = 'No Difference'


def create_sort_slice_session(session: Session, name: str, prompt: str, dataset: Dataset,
                              slices: List[ImageSlice]):
    label_session = LabelSession(
        dataset=dataset.name,
        session_name=name,
        session_type=LabelSessionType.SORT_SLICE.name,
        prompt=prompt,
        date_created=datetime.now(),
        label_values_str=SORT_LABEL_VALUES_STR,
        element_count=len(slices)
    )

    session.add(label_session)

    for i, sl in enumerate(slices):
        el = SessionElement(
            element_index=i,
            image_1_name=sl.image_name,
            slice_1_index=sl.slice_index,
            slice_1_type=sl.slice_type.name,
            session=label_session
        )
        session.add(el)

    session.commit()


def export_session_json(label_session: LabelSession) -> Dict:
    session_json = {
        'dataset': label_session.dataset,
        'session_name': label_session.session_name,
        'session_type': label_session.session_type,
        'prompt': label_session.prompt,
        'label_values_str': label_session.label_values_str
    }

    def conv_str(val) -> str:
        if val is None:
            return 'None'
        if type(val) is str:
            return val
        return str(val)

    skip_comparisons = label_session.session_type == LabelSessionType.SORT_SLICE.name

    elements_rows = []
    for el in label_session.elements:
        if skip_comparisons and el.is_comparison():
            continue
        elements_rows.append(','.join((
            conv_str(el.element_index),
            conv_str(el.image_1_name), conv_str(el.slice_1_type), conv_str(el.slice_1_index),
            conv_str(el.image_2_name), conv_str(el.slice_2_type), conv_str(el.slice_2_index)
        )))

    session_json['elements'] = elements_rows
    return session_json


def export_session(label_session: LabelSession) -> BytesIO:
    session_json = export_session_json(label_session)

    sio = StringIO()
    json.dump(session_json, sio, indent=1)

    bio = BytesIO()
    bio.write(sio.getvalue().encode('utf-8'))

    bio.seek(0)
    sio.close()

    return bio


def import_session_json(session: Session, dataset: Dataset, name: str, session_json: Dict):
    session_type = LabelSessionType[session_json['session_type']]
    prompt = session_json['prompt']
    label_values_str = session_json['label_values_str']

    assert type(prompt) is str
    assert type(label_values_str) is str

    label_session = LabelSession(
        dataset=dataset.name,
        session_name=name,
        session_type=session_type.name,
        prompt=prompt,
        date_created=datetime.now(),
        label_values_str=label_values_str,
        element_count=len(session_json['elements'])
    )

    session.add(label_session)

    for el_index, el_str in enumerate(session_json['elements']):
        el_split = el_str.split(',')
        image_1_name = None if el_split[1] == 'None' else el_split[1]
        slice_1_type = None if el_split[2] == 'None' else SliceType[el_split[2]].name
        slice_1_index = None if el_split[3] == 'None' else int(el_split[3])

        image_2_name = None if el_split[4] == 'None' else el_split[4]
        slice_2_type = None if el_split[5] == 'None' else SliceType[el_split[5]].name
        slice_2_index = None if el_split[6] == 'None' else int(el_split[6])

        assert type(image_1_name) is str
        assert image_2_name is None or type(image_2_name) is str

        el = SessionElement(
            element_index=el_index,
            image_1_name=image_1_name,
            slice_1_index=slice_1_index,
            slice_1_type=slice_1_type,
            image_2_name=image_2_name,
            slice_2_index=slice_2_index,
            slice_2_type=slice_2_type,
            session=label_session
        )

        session.add(el)

    session.commit()


def import_session(session: Session, dataset: Dataset, name: str, session_file: FileStorage):
    session_json = json.load(session_file.stream)
    import_session_json(session, dataset, name, session_json)

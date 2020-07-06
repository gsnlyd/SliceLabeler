import csv

from datetime import datetime
from io import StringIO, BytesIO
from typing import Dict, Optional, List

from sqlalchemy.orm import Session

from model import LabelSession, SessionElement, ElementLabel
from sessions import LabelSessionType


def get_element_by_index(session: Session, label_session: LabelSession, element_index: int) -> Optional[SessionElement]:
    return session.query(SessionElement) \
        .filter(SessionElement.session_id == label_session.id) \
        .filter(SessionElement.element_index == element_index) \
        .one_or_none()


def get_element_by_id(session: Session, element_id: int) -> Optional[SessionElement]:
    return session.query(SessionElement) \
        .filter(SessionElement.id == element_id) \
        .one_or_none()


def set_label(session: Session, element: SessionElement, label_value: str, ms: int):
    # TODO: validate label value
    label = ElementLabel(
        element_id=element.id,
        label_value=label_value,
        date_labeled=datetime.now(),
        milliseconds=ms
    )
    session.add(label)
    session.commit()


def get_all_labels(label_session: LabelSession) -> Dict[SessionElement, List[ElementLabel]]:
    return {el: el.labels for el in label_session.elements}


def export_labels(label_session: LabelSession):
    rows = []

    if label_session.session_type == LabelSessionType.CATEGORICAL_IMAGE.name:
        header = ('element_index', 'image_name', 'label_value', 'date_labeled', 'interaction_ms')
        for el in label_session.elements:
            for la in el.labels:
                rows.append((el.element_index, el.image_1_name, la.label_value, str(la.date_labeled), la.milliseconds))

    elif label_session.session_type == LabelSessionType.CATEGORICAL_SLICE.name:
        header = ('element_index',
                  'image_name', 'slice_type', 'slice_index',
                  'label_value', 'date_labeled', 'interaction_ms')
        for el in label_session.elements:
            for la in el.labels:
                rows.append((el.element_index,
                             el.image_1_name, el.slice_1_type, el.slice_1_index,
                             la.label_value, str(la.date_labeled), la.milliseconds))

    elif label_session.session_type == LabelSessionType.COMPARISON_SLICE.name:
        header = ('element_index',
                  'image_1_name', 'slice_1_type', 'slice_1_index',
                  'image_2_name', 'slice_2_type', 'slice_2_index',
                  'label_value', 'date_labeled', 'interaction_ms')
        for el in label_session.elements:
            for la in el.labels:
                rows.append((el.element_index,
                             el.image_1_name, el.slice_1_type, el.slice_1_index,
                             el.image_2_name, el.slice_2_type, el.slice_2_index,
                             la.label_value, str(la.date_labeled), la.milliseconds))
    else:  # Unknown type
        header = ()

    sio = StringIO()

    writer = csv.writer(sio)
    writer.writerow(header)
    for r in rows:
        writer.writerow(r)

    bio = BytesIO()
    bio.write(sio.getvalue().encode('utf-8'))

    bio.seek(0)
    sio.close()

    return bio

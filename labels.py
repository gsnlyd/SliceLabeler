from datetime import datetime
from typing import Dict, Optional, List

from sqlalchemy.orm import Session

from model import LabelSession, SessionElement, ElementLabel


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

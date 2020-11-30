from typing import List, Optional

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class LabelSession(db.Model):
    __tablename__ = 'label_sessions'

    id = db.Column(db.Integer, primary_key=True)
    dataset = db.Column(db.String(100), nullable=False)

    session_name = db.Column(db.String(100), nullable=False)
    session_type = db.Column(db.String(100), nullable=False)
    prompt = db.Column(db.String(1000), nullable=False)

    date_created = db.Column(db.DateTime, nullable=False)
    label_values_str = db.Column(db.String(1000), nullable=False)

    element_count = db.Column(db.Integer, nullable=False)

    elements: 'List[SessionElement]' = db.relationship('SessionElement', back_populates='session',
                                                       order_by='SessionElement.id')

    __table_args__ = (
        db.UniqueConstraint(dataset, session_name),
    )

    def label_values(self) -> List[str]:
        if self.label_values_str == '':
            return []
        return self.label_values_str.split(',')
    
    
class SessionElement(db.Model):
    __tablename__ = 'session_elements'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('label_sessions.id'), nullable=False)

    element_index = db.Column(db.Integer, nullable=False)

    image_1_name = db.Column(db.String(100), nullable=False)
    slice_1_index = db.Column(db.Integer, nullable=True)
    slice_1_type = db.Column(db.String(50), nullable=True)

    image_2_name = db.Column(db.String(100), nullable=True)
    slice_2_index = db.Column(db.Integer, nullable=True)
    slice_2_type = db.Column(db.String(50), nullable=True)
    
    session = db.relationship(LabelSession, back_populates='elements')
    labels: 'List[ElementLabel]' = db.relationship('ElementLabel', back_populates='element',
                                                   order_by='ElementLabel.id')

    def is_comparison(self) -> bool:
        return self.image_2_name is not None

    def current_label_value(self) -> Optional[str]:
        if len(self.labels) == 0:
            return None
        return self.labels[-1].label_value


class ElementLabel(db.Model):
    __tablename__ = 'element_labels'

    id = db.Column(db.Integer, primary_key=True)
    element_id = db.Column(db.Integer, db.ForeignKey('session_elements.id'), nullable=False)

    label_value = db.Column(db.String(100), nullable=False)

    date_labeled = db.Column(db.DateTime, nullable=False)
    milliseconds = db.Column(db.Integer, nullable=False)

    element = db.relationship(SessionElement, back_populates='labels')

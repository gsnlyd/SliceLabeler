from typing import List

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

    categorical_label_values = db.Column(db.String(1000), nullable=True)
    comparison_list_name = db.Column(db.String(200), nullable=True)

    categorical_labels: 'List[ImageLabel]' = db.relationship('ImageLabel', back_populates='session',
                                                             order_by='ImageLabel.id')
    comparison_labels: 'List[ComparisonLabel]' = db.relationship('ComparisonLabel', back_populates='session',
                                                                 order_by='ComparisonLabel.id')

    __table_args__ = (
        db.UniqueConstraint(dataset, session_name),
    )

    def label_values(self) -> List[str]:
        return self.categorical_label_values.split(',')


class ImageLabel(db.Model):
    __tablename__ = 'image_labels'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('label_sessions.id'), nullable=False)
    image_name = db.Column(db.String(100), nullable=False)

    date_labeled = db.Column(db.DateTime, nullable=False)
    label_value = db.Column(db.String(100), nullable=False)
    interaction_ms = db.Column(db.Integer, nullable=False)

    session = db.relationship(LabelSession, back_populates='categorical_labels')


class ComparisonLabel(db.Model):
    __tablename__ = 'comparison_labels'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('label_sessions.id'), nullable=False)
    comparison_index = db.Column(db.Integer, nullable=False)

    image_1_name = db.Column(db.String(100), nullable=False)
    slice_1_index = db.Column(db.Integer, nullable=False)
    slice_1_type = db.Column(db.String(50), nullable=False)

    image_2_name = db.Column(db.String(100), nullable=False)
    slice_2_index = db.Column(db.Integer, nullable=False)
    slice_2_type = db.Column(db.String(50), nullable=False)

    label_value = db.Column(db.String(50), nullable=False)
    date_labeled = db.Column(db.DateTime, nullable=False)

    time_taken_ms = db.Column(db.Integer, nullable=False)

    session = db.relationship(LabelSession, back_populates='comparison_labels')

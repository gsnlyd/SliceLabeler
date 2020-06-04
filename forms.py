from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, IntegerField, BooleanField
from wtforms.validators import Length, NumberRange

LENGTH_MESSAGE = 'Length must be between %(min)d and %(max)d.'


class CreateCategoricalSessionForm(FlaskForm):
    session_name = StringField('Session Name',
                               validators=[Length(3, 100, LENGTH_MESSAGE)],
                               render_kw={'placeholder': 'Session name'})
    prompt = StringField('Label Prompt',
                         validators=[Length(1, 100, LENGTH_MESSAGE)],
                         render_kw={'placeholder': 'Session prompt'})
    label_values = StringField('Label Values',
                               validators=[Length(1, 100, LENGTH_MESSAGE)],
                               render_kw={'placeholder': 'Session labels (comma-separated)'})
    submit_button = SubmitField('Create')


class CreateComparisonSessionForm(FlaskForm):
    session_name = StringField('Session Name',
                               validators=[Length(3, 100, LENGTH_MESSAGE)],
                               render_kw={'placeholder': 'Session name'})
    prompt = StringField('Label Prompt',
                         validators=[Length(1, 100, LENGTH_MESSAGE)],
                         render_kw={'placeholder': 'Session prompt'})
    comparison_list = SelectField('Comparison List', choices=[('create', 'Create New')])
    slice_type = SelectField('Orientation', choices=[('SAGITTAL', 'Sagittal'),
                                                     ('CORONAL', 'Coronal'),
                                                     ('AXIAL', 'Axial')])
    image_count = IntegerField('Number of Images')
    slice_count = IntegerField('Total Number of Slices', validators=[NumberRange(min=2)])
    comparison_count = IntegerField('Number of Comparisons', validators=[NumberRange(min=1)])
    min_slice_percent = IntegerField('Min Slice (%)', validators=[NumberRange(min=0, max=99)],
                                     render_kw={'placeholder': 'Min slice (%)'})
    max_slice_percent = IntegerField('Max Slice (%)', validators=[NumberRange(min=1, max=100)],
                                     render_kw={'placeholder': 'Max slice (%)'})
    submit_button = SubmitField('Create')

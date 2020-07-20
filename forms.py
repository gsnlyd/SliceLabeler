from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from wtforms import StringField, SubmitField, SelectField, IntegerField
from wtforms.validators import Length, NumberRange, Optional

LENGTH_MESSAGE = 'Length must be between %(min)d and %(max)d.'


class CreateCategoricalSessionForm(FlaskForm):
    session_name = StringField('Session Name',
                               validators=[Length(3, 100, LENGTH_MESSAGE)],
                               render_kw={'placeholder': 'My Session'})
    prompt = StringField('Label Prompt',
                         validators=[Length(0, 100, LENGTH_MESSAGE)],
                         render_kw={'placeholder': 'What is the level of artifacting in this image?'})
    label_values = StringField('Label Options',
                               validators=[Length(1, 100, LENGTH_MESSAGE)],
                               render_kw={'placeholder': 'None, Mild, Moderate, Severe'})
    submit_button = SubmitField('Create')


class CreateCategoricalSliceSessionForm(FlaskForm):
    session_name = StringField('Session Name',
                               validators=[Length(3, 100, LENGTH_MESSAGE)],
                               render_kw={'placeholder': 'My Session'})
    prompt = StringField('Label Prompt',
                         validators=[Length(0, 100, LENGTH_MESSAGE)],
                         render_kw={'placeholder': 'What is the level of artifacting in this slice?'})
    label_values = StringField('Label Options',
                               validators=[Length(1, 100, LENGTH_MESSAGE)],
                               render_kw={'placeholder': 'None, Mild, Moderate, Severe'})
    comparisons = SelectField('Use Slices From', choices=[])
    submit_button = SubmitField('Create')


class ComparisonNumberRange(NumberRange):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __call__(self, form, field):
        # Only validate comparison fields if new comparisons are being generated
        if form.comparisons.data == 'create':
            super().__call__(form, field)


class CreateComparisonSessionForm(FlaskForm):
    session_name = StringField('Session Name',
                               validators=[Length(3, 100, LENGTH_MESSAGE)],
                               render_kw={'placeholder': 'My Session'})
    prompt = StringField('Label Prompt',
                         validators=[Length(0, 100, LENGTH_MESSAGE)],
                         render_kw={'placeholder': 'Which slice has more severe artifacts?'})
    label_values = StringField('Additional Label Options',
                               validators=[Length(0, 100, LENGTH_MESSAGE)],
                               render_kw={'placeholder': 'No Difference, Not Sure',
                                          'value': 'No Difference, Not Sure'})
    comparisons = SelectField('Comparisons', choices=[('create', 'Create New')])
    slice_type = SelectField('Orientation', choices=[('SAGITTAL', 'Sagittal'),
                                                     ('CORONAL', 'Coronal'),
                                                     ('AXIAL', 'Axial')])
    image_count = IntegerField('Number of Images')

    slice_count = IntegerField('Total Number of Slices', validators=[ComparisonNumberRange(min=2)],
                               render_kw={'placeholder': 1000,
                                          'value': 1000})

    comparison_count = IntegerField('Number of Comparisons', validators=[ComparisonNumberRange(min=1)],
                                    render_kw={'placeholder': 2000,
                                               'value': 2000})

    max_comparisons_per_slice = IntegerField('Max Comparisons per Slice',
                                             validators=[Optional(), ComparisonNumberRange(min=1)],
                                             render_kw={'placeholder': 5})

    min_slice_percent = IntegerField('Min Slice (%)', validators=[ComparisonNumberRange(min=0, max=99)],
                                     render_kw={'placeholder': 0,
                                                'value': 0})

    max_slice_percent = IntegerField('Max Slice (%)', validators=[ComparisonNumberRange(min=1, max=100)],
                                     render_kw={'placeholder': 100,
                                                'value': 100})
    submit_button = SubmitField('Create')


class ImportSessionForm(FlaskForm):
    session_name = StringField('Session Name',
                               validators=[Length(3, 100, LENGTH_MESSAGE)],
                               render_kw={'placeholder': 'My Session'})
    session_file = FileField('Session File', validators=[FileRequired()])
    submit_button = SubmitField('Import')

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, IntegerField, BooleanField
from wtforms.validators import Length, NumberRange

LENGTH_MESSAGE = 'Length must be between %(min)d and %(max)d.'


class CreateCategoricalSessionForm(FlaskForm):
    session_name = StringField('Session Name',
                               validators=[Length(3, 100, LENGTH_MESSAGE)],
                               render_kw={'placeholder': 'My Session'})
    prompt = StringField('Label Prompt',
                         validators=[Length(0, 100, LENGTH_MESSAGE)],
                         render_kw={'placeholder': 'What do you think of this image?'})
    label_values = StringField('Label Options',
                               validators=[Length(1, 100, LENGTH_MESSAGE)],
                               render_kw={'placeholder': 'Amazing, Unremarkable, Boring'})
    submit_button = SubmitField('Create')


class CreateCategoricalSliceSessionForm(FlaskForm):
    session_name = StringField('Session Name',
                               validators=[Length(3, 100, LENGTH_MESSAGE)],
                               render_kw={'placeholder': 'My Session'})
    prompt = StringField('Label Prompt',
                         validators=[Length(0, 100, LENGTH_MESSAGE)],
                         render_kw={'placeholder': 'What do you think of this image?'})
    label_values = StringField('Label Options',
                               validators=[Length(1, 100, LENGTH_MESSAGE)],
                               render_kw={'placeholder': 'Amazing, Unremarkable, Boring'})
    comparison_list = SelectField('Comparison List', choices=[])
    submit_button = SubmitField('Create')


class ComparisonNumberRange(NumberRange):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __call__(self, form, field):
        # Only validate comparison list fields if a comparison list is actually being created
        if form.comparison_list.data == 'create':
            super().__call__(form, field)


class CreateComparisonSessionForm(FlaskForm):
    session_name = StringField('Session Name',
                               validators=[Length(3, 100, LENGTH_MESSAGE)],
                               render_kw={'placeholder': 'My Session'})
    prompt = StringField('Label Prompt',
                         validators=[Length(0, 100, LENGTH_MESSAGE)],
                         render_kw={'placeholder': 'Which image is your favorite?'})
    comparison_list = SelectField('Comparison List', choices=[('create', 'Create New')])
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

    min_slice_percent = IntegerField('Min Slice (%)', validators=[ComparisonNumberRange(min=0, max=99)],
                                     render_kw={'placeholder': 0,
                                                'value': 0})

    max_slice_percent = IntegerField('Max Slice (%)', validators=[ComparisonNumberRange(min=1, max=100)],
                                     render_kw={'placeholder': 100,
                                                'value': 100})
    submit_button = SubmitField('Create')

import os
from io import BytesIO
from typing import Dict, List

from flask import Flask, redirect, url_for, render_template, abort, request, jsonify, send_file

import backend
import labels
import sampling
import sessions
from forms import CreateCategoricalSessionForm, CreateComparisonSessionForm, ComparisonNumberRange, \
    CreateCategoricalSliceSessionForm
from model import db, LabelSession
from sessions import LabelSessionType

application = Flask(__name__)

application.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db/label_database.db'
application.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(application)

if not os.path.exists('db'):
    os.mkdir('db')

if not os.path.exists(backend.DATASETS_PATH):
    os.makedirs(backend.DATASETS_PATH, exist_ok=True)

with application.app_context():
    db.create_all()


@application.route('/')
def index():
    return redirect(url_for('dataset_list'))


@application.route('/thumb/<string:dataset_name>/<string:image_name>')
def thumbnail(dataset_name: str, image_name: str):
    dataset = backend.get_dataset(dataset_name)
    d_img = backend.get_image(dataset, image_name)

    slice_index = request.args.get('slice_index', default=0, type=int)
    slice_type_name = request.args.get('slice_type', default='AXIAL', type=str)

    intensity_min = request.args.get('min', default=0, type=int)
    intensity_max = request.args.get('max', default=0, type=int)

    slice_type = backend.SliceType[slice_type_name]

    slice_image = backend.get_slice(d_img, slice_index, slice_type, intensity_min, intensity_max)

    img_io = BytesIO()
    slice_image.save(img_io, 'PNG')
    img_io.seek(0)

    return send_file(img_io, mimetype='image/png')


@application.route('/export-labels/<int:session_id>')
def export_labels(session_id: int):
    label_session = sessions.get_session_by_id(db.session, session_id)
    if label_session is None:
        abort(400)

    labels_bytes = labels.export_labels(label_session)

    return send_file(labels_bytes,
                     mimetype='text/csv',
                     as_attachment=True,
                     attachment_filename=label_session.session_name + ' Labels.csv',
                     cache_timeout=0)


@application.route('/datasets')
def dataset_list():
    datasets = [(d, backend.get_images(d), sessions.get_sessions(db.session, d))
                for d in backend.get_datasets()]
    return render_template('dataset_list.html',
                           datasets=datasets)


@application.route('/dataset/<string:dataset_name>')
def dataset_overview(dataset_name: str):
    dataset = backend.get_dataset(dataset_name)
    if dataset is None:
        abort(404)

    images = backend.get_images(dataset)
    label_sessions = sessions.get_sessions(db.session, dataset)

    sessions_by_type: Dict[LabelSessionType, List[LabelSession]] = {st: [] for st in LabelSessionType}
    for sess in label_sessions:
        sessions_by_type[LabelSessionType[sess.session_type]].append(sess)

    return render_template('dataset_overview.html',
                           dataset=dataset,
                           images=images,
                           label_sessions=sessions_by_type)


@application.route('/session/<int:session_id>')
def session_overview(session_id: int):
    label_session = sessions.get_session_by_id(db.session, session_id)
    dataset = backend.get_dataset(label_session.dataset)

    resume_point = None
    for session_element in label_session.elements:
        if len(session_element.labels) == 0:
            resume_point = session_element.element_index
            break

    if label_session.session_type == LabelSessionType.CATEGORICAL_IMAGE.name:
        images = backend.get_images(dataset)
        return render_template('session_overview_categorical.html',
                               label_session=label_session,
                               dataset=dataset,
                               images=images,
                               resume_point=resume_point)

    elif label_session.session_type == LabelSessionType.CATEGORICAL_SLICE.name:
        return render_template('session_overview_categorical_slice.html',
                               label_session=label_session,
                               dataset=dataset,
                               resume_point=resume_point)
    else:  # COMPARISON_SLICE
        return render_template('session_overview_comparison.html',
                               label_session=label_session,
                               dataset=dataset,
                               resume_point=resume_point)


@application.route('/create-categorical-session/<string:dataset_name>', methods=['GET', 'POST'])
def create_categorical_session(dataset_name: str):
    dataset = backend.get_dataset(dataset_name)
    if dataset is None:
        abort(400)

    current_sessions = sessions.get_sessions(db.session, dataset)
    label_session_count = len(current_sessions)

    form = CreateCategoricalSessionForm(meta={'csrf': False})

    if form.validate_on_submit():
        if form.session_name.data in [se.session_name for se in current_sessions]:
            form.session_name.errors.append('Session name already in use.')
        else:
            label_values = [v.strip() for v in form.label_values.data.split(',')]
            sessions.create_categorical_image_session(db.session, form.session_name.data, form.prompt.data,
                                                      dataset, label_values)
            return redirect(url_for('dataset_overview', dataset_name=dataset.name))

    return render_template('create_categorical_session.html',
                           dataset=dataset,
                           label_session_count=label_session_count,
                           form=form)


@application.route('/create-categorical-slice-session/<string:dataset_name>', methods=['GET', 'POST'])
def create_categorical_slice_session(dataset_name: str):
    dataset = backend.get_dataset(dataset_name)
    if dataset is None:
        abort(400)

    current_sessions = sessions.get_sessions(db.session, dataset)
    label_session_count = len(current_sessions)

    form = CreateCategoricalSliceSessionForm(meta={'csrf': False})

    comparison_sessions = sessions.get_sessions(db.session, dataset, LabelSessionType.COMPARISON_SLICE)
    for sess in comparison_sessions:
        form.comparisons.choices.append((str(sess.id), sess.session_name))

    if form.validate_on_submit():
        if form.session_name.data in [se.session_name for se in current_sessions]:
            form.session_name.errors.append('Session name already in use.')
        else:
            label_values = [v.strip() for v in form.label_values.data.split(',')]

            from_session = sessions.get_session_by_id(db.session, int(form.comparisons.data))
            slices = sampling.get_slices_from_session(from_session)

            sessions.create_categorical_slice_session(db.session, form.session_name.data, form.prompt.data,
                                                      dataset, label_values, slices)
            return redirect(url_for('dataset_overview', dataset_name=dataset.name))

    return render_template('create_categorical_slice_session.html',
                           dataset=dataset,
                           label_session_count=label_session_count,
                           form=form)


@application.route('/create-comparison-session/<string:dataset_name>', methods=['GET', 'POST'])
def create_comparison_session(dataset_name: str):
    dataset = backend.get_dataset(dataset_name)
    if dataset is None:
        abort(400)

    current_sessions = sessions.get_sessions(db.session, dataset)
    label_session_count = len(current_sessions)

    images = backend.get_images(dataset)
    total_image_count = len(images)

    form = CreateComparisonSessionForm(meta={'csrf': False})

    comparison_sessions = sessions.get_sessions(db.session, dataset, LabelSessionType.COMPARISON_SLICE)
    for sess in comparison_sessions:
        form.comparisons.choices.append((str(sess.id), sess.session_name))

    form.image_count.validators.append(ComparisonNumberRange(
        min=1, max=total_image_count, message='Must be between %(min)s and %(max)s (the dataset size).'))

    if form.validate_on_submit():
        if form.session_name.data in [se.session_name for se in current_sessions]:
            form.session_name.errors.append('Session name already in use.')
        elif form.comparisons.data == 'create' and form.min_slice_percent.data >= form.max_slice_percent.data:
            form.max_slice_percent.errors.append('Max must be greater than min.')
        else:
            slice_type = backend.SliceType[form.slice_type.data]
            if form.comparisons.data == 'create':
                slices = sampling.sample_slices(dataset, slice_type, form.image_count.data, form.slice_count.data,
                                                form.min_slice_percent.data, form.max_slice_percent.data)
                comparisons = sampling.sample_comparisons(slices, form.comparison_count.data)
            else:
                from_session = sessions.get_session_by_id(db.session, int(form.comparisons.data))
                comparisons = sampling.get_comparisons_from_session(from_session)
            label_values = []  # TODO
            sessions.create_comparison_slice_session(db.session, form.session_name.data, form.prompt.data,
                                                     dataset, label_values, comparisons)
            return redirect(url_for('dataset_overview', dataset_name=dataset.name))

    return render_template('create_comparison_session.html',
                           dataset=dataset,
                           label_session_count=label_session_count,
                           total_image_count=total_image_count,
                           form=form)


@application.route('/viewer')
def viewer():
    dataset_name = request.args.get('dataset', type=str, default=None)
    image_name = request.args.get('image', type=str, default=None)

    if dataset_name is None or image_name is None:
        abort(400)

    dataset = backend.get_dataset(dataset_name)
    if dataset is None:
        abort(400)

    image = backend.get_image(dataset, image_name)
    if image is None:
        abort(400)

    slice_counts, max_value = backend.get_image_info(image)

    return render_template('viewer.html',
                           viewer_mode='viewer',
                           dataset=dataset,
                           image=image,
                           image_count=0,
                           image_index=0,
                           slice_counts=slice_counts,
                           image_max=max_value)


@application.route('/label')
def label():
    label_session_id = request.args.get('label_session', type=int, default=None)
    element_index = request.args.get('i', type=int, default=None)

    if label_session_id is None or element_index is None:
        abort(400)

    label_session = sessions.get_session_by_id(db.session, label_session_id)
    if label_session is None or label_session.session_type != LabelSessionType.CATEGORICAL_IMAGE.name:
        abort(400)

    dataset = backend.get_dataset(label_session.dataset)
    if dataset is None:
        abort(400)

    element = labels.get_element_by_index(db.session, label_session, element_index)
    image = backend.get_image(dataset, element.image_1_name)
    if image is None:
        abort(400)

    slice_counts, max_value = backend.get_image_info(image)

    image_label_value = element.current_label_value()

    return render_template('viewer.html',
                           viewer_mode='label',
                           label_session=label_session,
                           prompt=label_session.prompt,
                           dataset=dataset,
                           image=image,
                           element_id=element.id,
                           slice_counts=slice_counts,
                           image_max=max_value,
                           image_label_value=image_label_value,
                           previous_index=max(0, element_index - 1),
                           next_index=min(label_session.element_count - 1, element_index + 1))


@application.route('/label-categorical-slice')
def label_categorical_slice():
    label_session_id = request.args.get('label_session', type=int, default=None)
    element_index = request.args.get('i', type=int, default=None)

    if label_session_id is None or element_index is None:
        abort(400)

    label_session = sessions.get_session_by_id(db.session, label_session_id)
    if label_session is None or label_session.session_type != LabelSessionType.CATEGORICAL_SLICE.name:
        abort(400)

    dataset = backend.get_dataset(label_session.dataset)
    if dataset is None:
        abort(400)

    element = labels.get_element_by_index(db.session, label_session, element_index)
    image = backend.get_image(dataset, element.image_1_name)
    if image is None:
        abort(400)

    im_slice = backend.ImageSlice(element.image_1_name, element.slice_1_index, backend.SliceType[element.slice_1_type])

    _, max_value = backend.get_image_info(image)

    slice_label_value = element.current_label_value()
    return render_template('label_categorical_slice.html',
                           label_session=label_session,
                           dataset=dataset,
                           element_id=element.id,
                           image_slice=im_slice,
                           slice_label_value=slice_label_value,
                           image_max=max_value,
                           previous_index=max(0, element_index - 1),
                           next_index=min(label_session.element_count - 1, element_index + 1))


@application.route('/compare')
def label_compare():
    label_session_id = request.args.get('label_session', type=int, default=None)
    comparison_index = request.args.get('i', type=int, default=None)

    if label_session_id is None or comparison_index is None:
        abort(400)

    assert 0 <= comparison_index
    label_session = sessions.get_session_by_id(db.session, label_session_id)
    if label_session is None or label_session.session_type != LabelSessionType.COMPARISON_SLICE.name:
        abort(400)

    dataset = backend.get_dataset(label_session.dataset)
    if dataset is None:
        abort(400)

    element = labels.get_element_by_index(db.session, label_session, comparison_index)

    slice_1 = backend.ImageSlice(element.image_1_name, element.slice_1_index, backend.SliceType[element.slice_1_type])
    slice_2 = backend.ImageSlice(element.image_2_name, element.slice_2_index, backend.SliceType[element.slice_2_type])

    image_1 = backend.get_image(dataset, slice_1.image_name)
    image_2 = backend.get_image(dataset, slice_2.image_name)

    _, image_1_max = backend.get_image_info(image_1)
    _, image_2_max = backend.get_image_info(image_2)

    current_label_value = element.current_label_value()

    return render_template('label_compare.html',
                           label_session=label_session,
                           prompt=label_session.prompt,
                           dataset=dataset,
                           element_id=element.id,
                           slice_1=slice_1,
                           slice_2=slice_2,
                           image_1_max=image_1_max,
                           image_2_max=image_2_max,
                           current_label_value=current_label_value,
                           previous_index=max(0, comparison_index - 1),
                           next_index=min(label_session.element_count - 1, comparison_index + 1))


@application.route('/api/set-label-value', methods=['POST'])
def api_set_label():
    print(request.json)

    element = labels.get_element_by_id(db.session, request.json['element_id'])
    labels.set_label(db.session, element, request.json['label_value'], request.json['ms'])

    return jsonify({
        'Success': True
    })

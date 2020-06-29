import os
from io import BytesIO

from flask import Flask, redirect, url_for, render_template, abort, request, jsonify, send_file
from wtforms.validators import NumberRange

import backend
from backend import LabelSessionType
from forms import CreateCategoricalSessionForm, CreateComparisonSessionForm, ComparisonNumberRange, \
    CreateCategoricalSliceSessionForm
from model import db

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
    label_session = backend.get_label_session_by_id(db.session, session_id)
    if label_session is None:
        abort(400)

    labels_str = backend.export_labels(db.session, label_session)
    labels_bytes = BytesIO()
    labels_bytes.write(labels_str.getvalue().encode('utf-8'))

    labels_bytes.seek(0)
    labels_str.close()

    return send_file(labels_bytes,
                     mimetype='text/csv',
                     as_attachment=True,
                     attachment_filename=label_session.session_name + ' Labels.csv',
                     cache_timeout=0)


@application.route('/datasets')
def dataset_list():
    datasets = [(d, backend.get_images(d), backend.get_dataset_label_sessions(db.session, d))
                for d in backend.get_datasets()]
    return render_template('dataset_list.html',
                           datasets=datasets)


@application.route('/dataset/<string:dataset_name>')
def dataset_overview(dataset_name: str):
    dataset = backend.get_dataset(dataset_name)
    if dataset is None:
        abort(404)

    images = backend.get_images(dataset)
    label_sessions = backend.get_dataset_label_sessions(db.session, dataset)

    categorical_sessions = list(filter(lambda se: se.session_type == LabelSessionType.CATEGORICAL_VOLUME.value,
                                       label_sessions))
    categorical_slice_sessions = list(filter(lambda se: se.session_type == LabelSessionType.CATEGORICAL_SLICE.value,
                                             label_sessions))
    comparison_sessions = list(filter(lambda se: se.session_type == LabelSessionType.COMPARISON_SLICE.value,
                                      label_sessions))

    return render_template('dataset_overview.html',
                           dataset=dataset,
                           images=images,
                           label_sessions=label_sessions,
                           categorical_sessions=categorical_sessions,
                           categorical_slice_sessions=categorical_slice_sessions,
                           comparison_sessions=comparison_sessions)


@application.route('/session/<int:session_id>')
def session_overview(session_id: int):
    label_session = backend.get_label_session_by_id(db.session, session_id)
    dataset = backend.get_dataset(label_session.dataset)
    if label_session.session_type == 'comparison':
        comparison_list = backend.load_comparison_list(label_session.comparison_list_name)
        session_labels = backend.get_session_labels_comparison(db.session, label_session.id, comparison_list)

        resume_point = None
        for co_index, co_labels in enumerate(session_labels):
            if len(co_labels) == 0:
                resume_point = co_index
                break

        return render_template('session_overview_comparison.html',
                               label_session=label_session,
                               dataset=dataset,
                               comparison_list=comparison_list,
                               session_labels=session_labels,
                               resume_point=resume_point)
    else:
        images = backend.get_images(dataset)
        session_labels = backend.get_session_labels_categorical(db.session, label_session.id, images)

        resume_point = None
        for im_index, (im_name, im_labels) in enumerate(session_labels.items()):
            if len(im_labels) == 0:
                resume_point = im_index
                break

        return render_template('session_overview_categorical.html',
                               label_session=label_session,
                               dataset=dataset,
                               images=images,
                               session_labels=session_labels,
                               resume_point=resume_point)


@application.route('/create-categorical-session/<string:dataset_name>', methods=['GET', 'POST'])
def create_categorical_session(dataset_name: str):
    dataset = backend.get_dataset(dataset_name)
    if dataset is None:
        abort(400)

    current_sessions = backend.get_dataset_label_sessions(db.session, dataset)
    label_session_count = len(current_sessions)

    form = CreateCategoricalSessionForm(meta={'csrf': False})

    if form.validate_on_submit():
        if form.session_name.data in [se.session_name for se in current_sessions]:
            form.session_name.errors.append('Session name already in use.')
        else:
            label_values = [v.strip() for v in form.label_values.data.split(',')]
            backend.create_label_session(db.session, dataset, backend.LabelSessionType.CATEGORICAL_VOLUME,
                                         form.session_name.data, form.prompt.data,
                                         label_values=label_values)
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

    current_sessions = backend.get_dataset_label_sessions(db.session, dataset)
    label_session_count = len(current_sessions)

    form = CreateCategoricalSliceSessionForm(meta={'csrf': False})
    comparison_lists = backend.get_comparison_lists(dataset)
    for li in comparison_lists:
        form.comparison_list.choices.append((li, li))

    if form.validate_on_submit():
        if form.session_name.data in [se.session_name for se in current_sessions]:
            form.session_name.errors.append('Session name already in use.')
        else:
            assert form.comparison_list.data in comparison_lists
            label_values = [v.strip() for v in form.label_values.data.split(',')]
            backend.create_label_session(db.session, dataset, backend.LabelSessionType.CATEGORICAL_SLICE,
                                         form.session_name.data, form.prompt.data,
                                         comparison_list_name=form.comparison_list.data,
                                         label_values=label_values)
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

    current_sessions = backend.get_dataset_label_sessions(db.session, dataset)
    label_session_count = len(current_sessions)

    images = backend.get_images(dataset)
    total_image_count = len(images)

    comparison_lists = backend.get_comparison_lists(dataset)

    form = CreateComparisonSessionForm(meta={'csrf': False})
    for li in comparison_lists:
        form.comparison_list.choices.append((li, li))

    form.image_count.validators.append(ComparisonNumberRange(
        min=1, max=total_image_count, message='Must be between %(min)s and %(max)s (the dataset size).'))

    if form.validate_on_submit():
        if form.session_name.data in [se.session_name for se in current_sessions]:
            form.session_name.errors.append('Session name already in use.')
        elif form.comparison_list.data == 'create' and form.min_slice_percent.data >= form.max_slice_percent.data:
            form.max_slice_percent.errors.append('Max must be greater than min.')
        else:
            slice_type = backend.SliceType[form.slice_type.data]
            if form.comparison_list.data == 'create':
                comparison_list = backend.create_comparison_list(dataset, slice_type, form.image_count.data,
                                                                 form.slice_count.data, form.comparison_count.data,
                                                                 form.min_slice_percent.data,
                                                                 form.max_slice_percent.data)
            else:
                comparison_list = form.comparison_list.data
                assert comparison_list in comparison_lists
            backend.create_label_session(db.session, dataset, backend.LabelSessionType.COMPARISON_SLICE,
                                         form.session_name.data, form.prompt.data,
                                         comparison_list_name=comparison_list)
            return redirect(url_for('dataset_overview', dataset_name=dataset.name))

    return render_template('create_comparison_session.html',
                           dataset=dataset,
                           label_session_count=label_session_count,
                           total_image_count=total_image_count,
                           form=form)


@application.route('/viewer')
def viewer():
    dataset_name = request.args.get('dataset', type=str, default=None)
    image_index = request.args.get('i', type=int, default=None)

    if dataset_name is None or image_index is None:
        abort(400)

    dataset = backend.get_dataset(dataset_name)
    if dataset is None:
        abort(400)

    image, image_count = backend.get_image_by_index(dataset, image_index)
    if image is None:
        abort(400)

    slice_counts, max_value = backend.get_image_info(image)

    return render_template('viewer.html',
                           viewer_mode='viewer',
                           dataset=dataset,
                           image=image,
                           image_count=image_count,
                           image_index=image_index,
                           slice_counts=slice_counts,
                           image_max=max_value)


@application.route('/label')
def label():
    label_session_id = request.args.get('label_session', type=int, default=None)
    image_index = request.args.get('i', type=int, default=None)

    if label_session_id is None or image_index is None:
        abort(400)

    label_session = backend.get_label_session_by_id(db.session, label_session_id)
    if label_session is None or label_session.session_type != 'categorical':
        abort(400)

    dataset = backend.get_dataset(label_session.dataset)
    if dataset is None:
        abort(400)

    image, image_count = backend.get_image_by_index(dataset, image_index)
    if image is None:
        abort(400)

    slice_counts, max_value = backend.get_image_info(image)

    label_values = label_session.label_values()
    image_label_value = backend.get_current_categorical_label_value(db.session, label_session_id, image)

    return render_template('viewer.html',
                           viewer_mode='label',
                           label_session_id=label_session_id,
                           label_session=label_session,
                           prompt=label_session.prompt,
                           dataset=dataset,
                           image=image,
                           image_count=image_count,
                           image_index=image_index,
                           slice_counts=slice_counts,
                           image_max=max_value,
                           label_values=label_values,
                           image_label_value=image_label_value)


@application.route('/compare')
def label_compare():
    label_session_id = request.args.get('label_session', type=int, default=None)
    comparison_index = request.args.get('i', type=int, default=None)

    if label_session_id is None or comparison_index is None:
        abort(400)

    assert 0 <= comparison_index
    label_session = backend.get_label_session_by_id(db.session, label_session_id)
    if label_session is None or label_session.session_type != 'comparison':
        abort(400)

    dataset = backend.get_dataset(label_session.dataset)

    if dataset is None:
        abort(400)

    comparison_list = backend.load_comparison_list(label_session.comparison_list_name)
    slice_1, slice_2 = comparison_list[comparison_index]
    image_1 = backend.get_image(dataset, slice_1.image_name)
    image_2 = backend.get_image(dataset, slice_2.image_name)

    images = backend.get_images(dataset)
    image_1_index = images.index(image_1)
    image_2_index = images.index(image_2)

    _, image_1_max = backend.get_image_info(image_1)
    _, image_2_max = backend.get_image_info(image_2)

    current_label_value = backend.get_current_comparison_label_value(db.session, label_session_id, comparison_index)

    return render_template('label_compare.html',
                           label_session_id=label_session_id,
                           label_session=label_session,
                           prompt=label_session.prompt,
                           dataset=dataset,
                           comparison_index=comparison_index,
                           slice_1=slice_1,
                           slice_2=slice_2,
                           image_1_max=image_1_max,
                           image_2_max=image_2_max,
                           image_1_index=image_1_index,
                           image_2_index=image_2_index,
                           current_label_value=current_label_value,
                           previous_index=max(0, comparison_index - 1),
                           next_index=min(len(comparison_list) - 1, comparison_index + 1))


@application.route('/api/set-label-value', methods=['POST'])
def api_set_label():
    print(request.json)

    label_session = backend.get_label_session_by_id(db.session, request.json['label_session_id'])
    if label_session is None:
        abort(400)

    dataset = backend.get_dataset(label_session.dataset)
    image = backend.get_image(dataset, request.json['image_name'])
    if image is None:
        abort(400)

    backend.set_categorical_label(
        session=db.session,
        label_session=label_session,
        image=image,
        label_value=request.json['label_value'],
        interaction_ms=request.json['interaction_ms']
    )

    return jsonify({
        'Success': True
    })


@application.route('/api/set-comparison-label-value', methods=['POST'])
def api_set_comparison_label():
    print(request.json)

    label_session = backend.get_label_session_by_id(db.session, request.json['label_session_id'])
    if label_session is None:
        abort(400)

    comparison_index = request.json['comparison_index']
    if type(comparison_index) is not int:
        abort(400)

    label_value = request.json['label_value']
    time_taken_ms = request.json['time_taken_ms']
    if type(time_taken_ms) is not int:
        abort(400)

    backend.set_comparison_label(db.session, label_session, comparison_index, label_value, time_taken_ms)

    return jsonify({
        'success': True
    })

import os
from io import BytesIO
from typing import Dict, List

from flask import Flask, redirect, url_for, render_template, abort, request, jsonify, send_file
from wtforms.validators import NumberRange

import backend
import comparesort
import labels
import ranking
import sampling
import sessions
import thumbnails
from forms import CreateCategoricalSessionForm, CreateComparisonSessionForm, ComparisonNumberRange, \
    CreateCategoricalSliceSessionForm, ImportSessionForm, CreateSortSessionForm
from model import db, LabelSession
from sessions import LabelSessionType

application = Flask(__name__)

DB_DIR_PATH = 'db'
DB_FILE_NAME = 'label_database.db'

application.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(DB_DIR_PATH, DB_FILE_NAME)
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


@application.route('/export-session/<int:session_id>')
def export_session(session_id: int):
    label_session = sessions.get_session_by_id(db.session, session_id)
    if label_session is None:
        abort(400)

    session_bytes = sessions.export_session(label_session)
    return send_file(session_bytes,
                     mimetype='application/json',
                     as_attachment=True,
                     attachment_filename=label_session.session_name + '.json',
                     cache_timeout=0)


@application.route('/generate-thumbnails/<int:session_id>')
def generate_thumbnails(session_id: int):
    label_session = sessions.get_session_by_id(db.session, session_id)
    if label_session is None:
        abort(400)
    thumbnails.create_thumbnails(label_session)
    return redirect(url_for('slice_rankings', session_id=session_id))


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
    elif label_session.session_type == LabelSessionType.COMPARISON_SLICE.name:
        return render_template('session_overview_comparison.html',
                               label_session=label_session,
                               dataset=dataset,
                               resume_point=resume_point)
    elif label_session.session_type == LabelSessionType.SORT_SLICE.name:
        labels_complete = comparesort.add_next_comparison(db.session, label_session)[0]
        return render_template('session_overview_sort.html',
                               label_session=label_session,
                               dataset=dataset,
                               resume_point=resume_point,
                               labels_complete=labels_complete,
                               slice_elements=[el for el in label_session.elements if not el.is_comparison()],
                               comparison_elements=[el for el in label_session.elements if el.is_comparison()])
    else:
        abort(500)


@application.route('/slice-rankings/<int:session_id>')
def slice_rankings(session_id: int):
    label_session = sessions.get_session_by_id(db.session, session_id)

    if label_session.session_type == LabelSessionType.COMPARISON_SLICE.name:
        ranked_slices = ranking.rank_slices(label_session)
    elif label_session.session_type == LabelSessionType.SORT_SLICE.name:
        complete, _, sorted_slices = comparesort.add_next_comparison(db.session, label_session)
        if not complete:
            abort(400)
        ranked_slices = [(sl, None) for sl in reversed(sorted_slices)]
    else:
        abort(400)

    thumbs_data = thumbnails.get_thumbnails(label_session)
    num_thumbs_missing = len([d for d in thumbs_data.values() if not d.exists])

    return render_template('slice_rankings.html',
                           label_session=label_session,
                           ranked_slices=ranked_slices,
                           thumbs_data=thumbs_data,
                           num_thumbs_missing=num_thumbs_missing)


@application.route('/import-session/<string:dataset_name>', methods=['GET', 'POST'])
def import_session(dataset_name: str):
    dataset = backend.get_dataset(dataset_name)
    if dataset is None:
        abort(400)

    form = ImportSessionForm(meta={'csrf': False})

    if form.validate_on_submit():
        sessions.import_session(db.session, dataset, form.session_name.data, form.session_file.data)
        return redirect(url_for('dataset_overview', dataset_name=dataset.name))

    label_session_count = len(sessions.get_sessions(db.session, dataset))

    return render_template('import_session.html',
                           dataset=dataset,
                           form=form,
                           label_session_count=label_session_count)


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

    form.image_count.validators = [
        ComparisonNumberRange(min=1, max=total_image_count,
                              message='Must be between %(min)s and %(max)s (the dataset size).')
    ]

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
                if form.comparison_count.data is None:
                    comparisons = sampling.all_comparisons(slices)
                else:
                    comparisons = sampling.sample_comparisons(slices, form.comparison_count.data,
                                                              form.max_comparisons_per_slice.data)
            else:
                from_session = sessions.get_session_by_id(db.session, int(form.comparisons.data))
                comparisons = sampling.get_comparisons_from_session(from_session)
            label_values = [v.strip() for v in form.label_values.data.split(',')]
            sessions.create_comparison_slice_session(db.session, form.session_name.data, form.prompt.data,
                                                     dataset, label_values, comparisons)
            return redirect(url_for('dataset_overview', dataset_name=dataset.name))

    return render_template('create_comparison_session.html',
                           dataset=dataset,
                           label_session_count=label_session_count,
                           total_image_count=total_image_count,
                           form=form)


SLICE_SESSION_NAMES = (
    LabelSessionType.COMPARISON_SLICE.name,
    LabelSessionType.CATEGORICAL_SLICE.name,
    LabelSessionType.SORT_SLICE.name
)


@application.route('/create-sort-session/<string:dataset_name>', methods=['GET', 'POST'])
def create_sort_session(dataset_name: str):
    dataset = backend.get_dataset(dataset_name)
    if dataset is None:
        abort(400)

    current_sessions = sessions.get_sessions(db.session, dataset)
    label_session_count = len(current_sessions)

    images = backend.get_images(dataset)
    total_image_count = len(images)

    form = CreateSortSessionForm(meta={'csrf': False})

    form.image_count.validators = [
        NumberRange(min=1, max=total_image_count, message='Must be between %(min)s and %(max)s (the dataset size).')
    ]
    for sess in sessions.get_sessions(db.session, dataset):
        t = sess.session_type
        if t in SLICE_SESSION_NAMES:
            form.slices_from.choices.append((str(sess.id), sess.session_name))

    if form.validate_on_submit():
        if form.session_name.data in [se.session_name for se in current_sessions]:
            form.session_name.errors.append('Session name already in use.')
        elif form.min_slice_percent.data >= form.max_slice_percent.data:
            form.max_slice_percent.errors.append('Max must be greater than min.')
        else:
            if form.slices_from.data == 'create':
                slice_type = backend.SliceType[form.slice_type.data]
                slices = sampling.sample_slices(dataset, slice_type, form.image_count.data, form.slice_count.data,
                                                form.min_slice_percent.data, form.max_slice_percent.data)
            else:
                from_session = sessions.get_session_by_id(db.session, int(form.slices_from.data))
                slices = sampling.get_slices_from_session(from_session)

            sessions.create_sort_slice_session(db.session, form.session_name.data, form.prompt.data, dataset, slices)
            return redirect(url_for('dataset_overview', dataset_name=dataset.name))
    return render_template('create_sort_session.html',
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
                           sort_mode=False,
                           previous_index=max(0, comparison_index - 1),
                           next_index=min(label_session.element_count - 1, comparison_index + 1))


@application.route('/sort-compare')
def label_sort_compare():
    label_session_id = request.args.get('label_session')
    if label_session_id is None:
        abort(404)

    label_session = sessions.get_session_by_id(db.session, label_session_id)
    if label_session is None:
        abort(404)
    if label_session.session_type != LabelSessionType.SORT_SLICE.name:
        abort(400)

    dataset = backend.get_dataset(label_session.dataset)
    if dataset is None:
        abort(404)

    complete, comparison_el, _ = comparesort.add_next_comparison(db.session, label_session)
    if complete:
        return redirect(url_for('session_overview', session_id=label_session.id))

    comparison = sampling.get_comparison_from_element(comparison_el)
    slice_1, slice_2 = comparison

    image_1 = backend.get_image(dataset, slice_1.image_name)
    image_2 = backend.get_image(dataset, slice_2.image_name)

    _, image_1_max = backend.get_image_info(image_1)
    _, image_2_max = backend.get_image_info(image_2)

    current_label_value = None

    return render_template('label_compare.html',
                           label_session=label_session,
                           prompt=label_session.prompt,
                           dataset=dataset,
                           element_id=comparison_el.id,
                           slice_1=slice_1,
                           slice_2=slice_2,
                           image_1_max=image_1_max,
                           image_2_max=image_2_max,
                           current_label_value=current_label_value,
                           sort_mode=True)


@application.route('/api/set-label-value', methods=['POST'])
def api_set_label():
    print(request.json)

    element = labels.get_element_by_id(db.session, request.json['element_id'])
    labels.set_label(db.session, element, request.json['label_value'], request.json['ms'])

    return jsonify({
        'Success': True
    })

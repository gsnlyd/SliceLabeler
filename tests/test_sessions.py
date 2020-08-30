import os

from flask import Flask
from flask_testing import TestCase
from pyfakefs.fake_filesystem_unittest import TestCaseMixin

import backend
from backend import SliceType, ImageSlice
import sessions
from sessions import LabelSessionType
from model import db


class TestSessions(TestCase, TestCaseMixin):
    def create_app(self):
        application = Flask(__name__)
        application.config['TESTING'] = True

        # Empty SQLite URI points to in-memory database
        application.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
        application.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        db.init_app(application)

        return application

    def setUp(self):
        self.setUpPyfakefs()
        db.create_all()

        self.fs.create_dir(backend.DATASETS_PATH)

        self.fs.create_file(os.path.join(backend.DATASETS_PATH, 'dataset1', 'img1.nii.gz'))
        self.fs.create_file(os.path.join(backend.DATASETS_PATH, 'dataset1', 'img2.nii'))
        self.fs.create_dir(os.path.join(backend.DATASETS_PATH, 'dataset1', 'img3'))

        self.fs.create_dir(os.path.join(backend.DATASETS_PATH, 'dataset2'))
        self.fs.create_dir(os.path.join(backend.DATASETS_PATH, 'dataset3'))

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_get_session_by_id(self):
        dataset = backend.get_dataset('dataset1')
        sessions.create_categorical_image_session(db.session, 'session1', 'prompt', dataset, ['l1', 'l2', 'l3'])
        label_session = sessions.get_session_by_id(db.session, 1)

        self.assertEqual(label_session.session_name, 'session1')

    def test_get_session_by_id_non_existent(self):
        non_existent_session = sessions.get_session_by_id(db.session, 1)
        self.assertIsNone(non_existent_session)

    def test_get_sessions_length(self):
        dataset1 = backend.get_dataset('dataset1')
        dataset2 = backend.get_dataset('dataset2')

        sessions.create_categorical_image_session(db.session, 'session1', 'prompt', dataset1, ['l1', 'l2', 'l3'])
        sessions.create_categorical_image_session(db.session, 'session2', 'prompt', dataset1, ['l1', 'l2', 'l3'])
        sessions.create_categorical_image_session(db.session, 'session3', 'prompt', dataset1, ['l1', 'l2', 'l3'])
        sessions.create_categorical_image_session(db.session, 'session4', 'prompt', dataset2, ['l1', 'l2', 'l3'])

        dataset1_sessions = sessions.get_sessions(db.session, dataset1)
        dataset1_sessions_count = len(dataset1_sessions)

        dataset2_sessions = sessions.get_sessions(db.session, dataset2)
        dataset2_sessions_count = len(dataset2_sessions)

        self.assertEqual(dataset1_sessions_count, 3)
        self.assertEqual(dataset2_sessions_count, 1)

    def test_get_sessions_by_type_length(self):
        dataset = backend.get_dataset('dataset1')

        sessions.create_categorical_image_session(db.session, 'session1', 'prompt', dataset, ['l1', 'l2', 'l3'])
        sessions.create_categorical_image_session(db.session, 'session2', 'prompt', dataset, ['l1', 'l2', 'l3'])

        sessions.create_categorical_slice_session(db.session, 'session3', 'prompt', dataset, ['l1', 'l2', 'l3'], [])
        sessions.create_categorical_slice_session(db.session, 'session4', 'prompt', dataset, ['l1', 'l2', 'l3'], [])

        sessions.create_comparison_slice_session(db.session, 'session5', 'prompt', dataset, ['l1', 'l2'], [])

        sessions.create_categorical_image_session(db.session, 'session6', 'prompt', dataset, ['l1', 'l2', 'l3'])
        sessions.create_categorical_image_session(db.session, 'session7', 'prompt', dataset, ['l1', 'l2', 'l3'])

        categorical_image_sessions = sessions.get_sessions(db.session, dataset, LabelSessionType.CATEGORICAL_IMAGE)
        categorical_image_session_count = len(categorical_image_sessions)

        categorical_slice_sessions = sessions.get_sessions(db.session, dataset, LabelSessionType.CATEGORICAL_SLICE)
        categorical_slice_session_count = len(categorical_slice_sessions)

        comparison_slice_sessions = sessions.get_sessions(db.session, dataset, LabelSessionType.COMPARISON_SLICE)
        comparison_slice_session_count = len(comparison_slice_sessions)

        self.assertEqual(categorical_image_session_count, 4)
        self.assertEqual(categorical_slice_session_count, 2)
        self.assertEqual(comparison_slice_session_count, 1)

    def test_get_sessions_empty(self):
        dataset = backend.get_dataset('dataset1')
        label_sessions = sessions.get_sessions(db.session, dataset)
        label_session_count = len(label_sessions)

        self.assertEqual(label_session_count, 0)

    def test_create_categorical_image_session_metadata(self):
        dataset = backend.get_dataset('dataset1')
        sessions.create_categorical_image_session(db.session, 'session1', 'test_prompt', dataset, ['l1', 'l2', 'l3'])
        label_session = sessions.get_session_by_id(db.session, 1)

        self.assertEqual(label_session.session_name, 'session1')
        self.assertEqual(label_session.session_type, LabelSessionType.CATEGORICAL_IMAGE.name)
        self.assertEqual(label_session.prompt, 'test_prompt')
        self.assertEqual(label_session.dataset, 'dataset1')
        self.assertEqual(label_session.label_values_str, 'l1,l2,l3')

    def test_create_categorical_image_session_elements_length(self):
        dataset = backend.get_dataset('dataset1')
        sessions.create_categorical_image_session(db.session, 'session1', 'test_prompt', dataset, ['l1', 'l2', 'l3'])

        label_session = sessions.get_session_by_id(db.session, 1)
        session_elements = label_session.elements

        session_elements_count = len(session_elements)
        self.assertEqual(session_elements_count, 3)

    def test_create_categorical_image_session_elements_metadata(self):
        dataset = backend.get_dataset('dataset1')
        sessions.create_categorical_image_session(db.session, 'session1', 'test_prompt', dataset, ['l1', 'l2', 'l3'])

        label_session = sessions.get_session_by_id(db.session, 1)
        session_elements = label_session.elements

        self.assertEqual(session_elements[0].element_index, 0)
        self.assertEqual(session_elements[1].element_index, 1)
        self.assertEqual(session_elements[2].element_index, 2)

        self.assertEqual(session_elements[0].image_1_name, 'img1.nii.gz')
        self.assertEqual(session_elements[1].image_1_name, 'img2.nii')
        self.assertEqual(session_elements[2].image_1_name, 'img3')

        self.assertIsNone(session_elements[0].slice_1_index)
        self.assertIsNone(session_elements[0].slice_1_type)
        self.assertIsNone(session_elements[0].image_2_name)
        self.assertIsNone(session_elements[0].slice_2_index)
        self.assertIsNone(session_elements[0].slice_2_type)

    def test_create_categorical_slice_session_metadata(self):
        dataset = backend.get_dataset('dataset1')
        sessions.create_categorical_slice_session(db.session, 'session1', 'test_prompt', dataset,
                                                  ['l1', 'l2', 'l3'], [])
        label_session = sessions.get_session_by_id(db.session, 1)

        self.assertEqual(label_session.session_name, 'session1')
        self.assertEqual(label_session.session_type, LabelSessionType.CATEGORICAL_SLICE.name)
        self.assertEqual(label_session.prompt, 'test_prompt')
        self.assertEqual(label_session.dataset, 'dataset1')
        self.assertEqual(label_session.label_values_str, 'l1,l2,l3')

    def test_create_categorical_slice_session_elements_length(self):
        dataset = backend.get_dataset('dataset1')
        slices = [
            ImageSlice('img1.nii.gz', 0, SliceType.SAGITTAL),
            ImageSlice('img1.nii.gz', 100, SliceType.SAGITTAL),
            ImageSlice('img2.nii', 1, SliceType.CORONAL),
            ImageSlice('img3', 255, SliceType.AXIAL)
        ]
        sessions.create_categorical_slice_session(db.session, 'session1', 'test_prompt', dataset,
                                                  ['l1', 'l2', 'l3'], slices)
        label_session = sessions.get_session_by_id(db.session, 1)
        session_elements = label_session.elements

        session_element_count = len(session_elements)
        self.assertEqual(session_element_count, 4)

    def test_create_categorical_slice_session_elements_metadata(self):
        dataset = backend.get_dataset('dataset1')
        slices = [
            ImageSlice('img1.nii.gz', 0, SliceType.SAGITTAL),
            ImageSlice('img1.nii.gz', 100, SliceType.SAGITTAL),
            ImageSlice('img2.nii', 1, SliceType.CORONAL),
            ImageSlice('img3', 255, SliceType.AXIAL)
        ]
        sessions.create_categorical_slice_session(db.session, 'session1', 'test_prompt', dataset,
                                                  ['l1', 'l2', 'l3'], slices)
        label_session = sessions.get_session_by_id(db.session, 1)
        session_elements = label_session.elements

        self.assertEqual(session_elements[0].element_index, 0)
        self.assertEqual(session_elements[1].element_index, 1)
        self.assertEqual(session_elements[2].element_index, 2)
        self.assertEqual(session_elements[3].element_index, 3)

        self.assertEqual(session_elements[0].image_1_name, 'img1.nii.gz')
        self.assertEqual(session_elements[1].image_1_name, 'img1.nii.gz')
        self.assertEqual(session_elements[2].image_1_name, 'img2.nii')
        self.assertEqual(session_elements[3].image_1_name, 'img3')

        self.assertEqual(session_elements[0].slice_1_type, SliceType.SAGITTAL.name)
        self.assertEqual(session_elements[1].slice_1_type, SliceType.SAGITTAL.name)
        self.assertEqual(session_elements[2].slice_1_type, SliceType.CORONAL.name)
        self.assertEqual(session_elements[3].slice_1_type, SliceType.AXIAL.name)

        self.assertEqual(session_elements[0].slice_1_index, 0)
        self.assertEqual(session_elements[1].slice_1_index, 100)
        self.assertEqual(session_elements[2].slice_1_index, 1)
        self.assertEqual(session_elements[3].slice_1_index, 255)

    def test_create_comparison_slice_session_metadata(self):
        dataset = backend.get_dataset('dataset1')
        sessions.create_comparison_slice_session(db.session, 'session1', 'test_prompt', dataset, ['l1', 'l2', 'l3'], [])
        label_session = sessions.get_session_by_id(db.session, 1)

        self.assertEqual(label_session.session_name, 'session1')
        self.assertEqual(label_session.session_type, LabelSessionType.COMPARISON_SLICE.name)
        self.assertEqual(label_session.prompt, 'test_prompt')
        self.assertEqual(label_session.dataset, 'dataset1')
        self.assertEqual(label_session.label_values_str, 'l1,l2,l3')

    def test_create_comparison_slice_session_elements_length(self):
        dataset = backend.get_dataset('dataset1')
        comparisons = [
            (ImageSlice('img1.nii.gz', 0, SliceType.SAGITTAL), ImageSlice('img3', 1, SliceType.CORONAL)),
            (ImageSlice('img2.nii', 0, SliceType.SAGITTAL), ImageSlice('img3', 1, SliceType.AXIAL)),
            (ImageSlice('img2.nii', 255, SliceType.CORONAL), ImageSlice('img1.nii.gz', 100, SliceType.AXIAL))
        ]
        sessions.create_comparison_slice_session(db.session, 'session1', 'test_prompt', dataset,
                                                 ['l1', 'l2', 'l3'], comparisons)
        label_session = sessions.get_session_by_id(db.session, 1)
        session_elements = label_session.elements

        session_element_count = len(session_elements)
        self.assertEqual(session_element_count, 3)

    def test_create_comparison_slice_session_elements_metadata(self):
        dataset = backend.get_dataset('dataset1')
        comparisons = [
            (ImageSlice('img1.nii.gz', 0, SliceType.SAGITTAL), ImageSlice('img3', 1, SliceType.CORONAL)),
            (ImageSlice('img2.nii', 0, SliceType.SAGITTAL), ImageSlice('img3', 1, SliceType.AXIAL)),
            (ImageSlice('img2.nii', 255, SliceType.CORONAL), ImageSlice('img1.nii.gz', 100, SliceType.AXIAL))
        ]
        sessions.create_comparison_slice_session(db.session, 'session1', 'test_prompt', dataset,
                                                 ['l1', 'l2', 'l3'], comparisons)
        label_session = sessions.get_session_by_id(db.session, 1)
        session_elements = label_session.elements

        self.assertEqual(session_elements[0].image_1_name, 'img1.nii.gz')
        self.assertEqual(session_elements[0].image_2_name, 'img3')

        self.assertEqual(session_elements[1].slice_1_index, 0)
        self.assertEqual(session_elements[1].slice_2_index, 1)

        self.assertEqual(session_elements[2].slice_1_type, SliceType.CORONAL.name)
        self.assertEqual(session_elements[2].slice_2_type, SliceType.AXIAL.name)

    def test_export_session_json_metadata(self):
        dataset = backend.get_dataset('dataset1')
        sessions.create_categorical_image_session(db.session, 'session1', 'test_prompt', dataset, ['l1', 'l2', 'l3'])

        label_session = sessions.get_session_by_id(db.session, 1)
        session_json = sessions.export_session_json(label_session)

        self.assertEqual(session_json['dataset'], 'dataset1')
        self.assertEqual(session_json['session_name'], 'session1')
        self.assertEqual(session_json['session_type'], LabelSessionType.CATEGORICAL_IMAGE.name)
        self.assertEqual(session_json['prompt'], 'test_prompt')
        self.assertEqual(session_json['label_values_str'], 'l1,l2,l3')

    def test_export_session_json_elements_length(self):
        dataset = backend.get_dataset('dataset1')
        sessions.create_categorical_image_session(db.session, 'session1', 'test_prompt', dataset, ['l1', 'l2', 'l3'])

        label_session = sessions.get_session_by_id(db.session, 1)
        session_json = sessions.export_session_json(label_session)

        element_count = len(session_json['elements'])
        self.assertEqual(element_count, 3)

    def test_export_session_json_elements_metadata(self):
        dataset = backend.get_dataset('dataset1')
        comparisons = [
            (ImageSlice('img1.nii.gz', 0, SliceType.SAGITTAL), ImageSlice('img3', 1, SliceType.CORONAL)),
            (ImageSlice('img2.nii', 0, SliceType.SAGITTAL), ImageSlice('img3', 1, SliceType.AXIAL)),
            (ImageSlice('img2.nii', 255, SliceType.CORONAL), ImageSlice('img1.nii.gz', 100, SliceType.AXIAL))
        ]
        sessions.create_comparison_slice_session(db.session, 'session1', 'test_prompt', dataset,
                                                 ['l1', 'l2', 'l3'], comparisons)
        label_session = sessions.get_session_by_id(db.session, 1)

        session_json = sessions.export_session_json(label_session)
        elements_json = session_json['elements']

        self.assertEqual(elements_json[0], '0,img1.nii.gz,SAGITTAL,0,img3,CORONAL,1')
        self.assertEqual(elements_json[1], '1,img2.nii,SAGITTAL,0,img3,AXIAL,1')
        self.assertEqual(elements_json[2], '2,img2.nii,CORONAL,255,img1.nii.gz,AXIAL,100')

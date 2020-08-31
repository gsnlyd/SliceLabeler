import os

from flask import Flask
from flask_testing import TestCase
from pyfakefs.fake_filesystem_unittest import TestCaseMixin

import backend
import labels
import sessions
from model import db


class TestSampling(TestCase, TestCaseMixin):
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

    def test_get_element_by_index(self):
        dataset = backend.get_dataset('dataset1')
        sessions.create_categorical_image_session(db.session, 'session1', 'prompt', dataset, ['l1', 'l2', 'l3'])
        label_session = sessions.get_session_by_id(db.session, 1)

        element = labels.get_element_by_index(db.session, label_session, 0)
        self.assertEqual(element.image_1_name, 'img1.nii.gz')

    def test_get_element_by_id(self):
        dataset = backend.get_dataset('dataset1')
        sessions.create_categorical_image_session(db.session, 'session1', 'prompt', dataset, ['l1', 'l2', 'l3'])

        element = labels.get_element_by_id(db.session, 1)
        self.assertEqual(element.image_1_name, 'img1.nii.gz')

    def test_set_label(self):
        dataset = backend.get_dataset('dataset1')
        sessions.create_categorical_image_session(db.session, 'session1', 'prompt', dataset, ['l1', 'l2', 'l3'])
        element = labels.get_element_by_id(db.session, 1)

        labels.set_label(db.session, element, 'l1', 1000)

        label_count = len(element.labels)
        self.assertEqual(label_count, 1)

        element_label = element.labels[0]
        self.assertEqual(element_label.label_value, 'l1')
        self.assertEqual(element_label.milliseconds, 1000)

    def test_get_all_labels_elements_length(self):
        dataset = backend.get_dataset('dataset1')
        sessions.create_categorical_image_session(db.session, 'session1', 'prompt', dataset, ['l1', 'l2', 'l3'])
        label_session = sessions.get_session_by_id(db.session, 1)
        all_labels = labels.get_all_labels(label_session)

        element_count = len(all_labels)
        self.assertEqual(element_count, 3)

    def test_get_all_labels_elements_metadata(self):
        dataset = backend.get_dataset('dataset1')
        sessions.create_categorical_image_session(db.session, 'session1', 'prompt', dataset, ['l1', 'l2', 'l3'])
        label_session = sessions.get_session_by_id(db.session, 1)
        all_labels = labels.get_all_labels(label_session)

        check_elements = list(all_labels.keys())
        self.assertEqual(check_elements, label_session.elements)

    def test_get_all_labels_labels_length(self):
        dataset = backend.get_dataset('dataset1')
        sessions.create_categorical_image_session(db.session, 'session1', 'prompt', dataset, ['l1', 'l2', 'l3'])
        label_session = sessions.get_session_by_id(db.session, 1)

        labels.set_label(db.session, label_session.elements[0], 'l1', 1000)
        labels.set_label(db.session, label_session.elements[0], 'l2', 250)
        labels.set_label(db.session, label_session.elements[1], 'l3', 0)

        all_labels = labels.get_all_labels(label_session)
        check_labels = list(all_labels.values())

        self.assertEqual(len(check_labels[0]), 2)
        self.assertEqual(len(check_labels[1]), 1)
        self.assertEqual(len(check_labels[2]), 0)

    def test_get_all_labels_labels_metadata(self):
        dataset = backend.get_dataset('dataset1')
        sessions.create_categorical_image_session(db.session, 'session1', 'prompt', dataset, ['l1', 'l2', 'l3'])
        label_session = sessions.get_session_by_id(db.session, 1)

        labels.set_label(db.session, label_session.elements[0], 'l1', 1000)
        labels.set_label(db.session, label_session.elements[0], 'l2', 250)
        labels.set_label(db.session, label_session.elements[1], 'l3', 0)

        all_labels = labels.get_all_labels(label_session)
        check_labels = list(all_labels.values())

        self.assertEqual(check_labels[0][0].label_value, 'l1')
        self.assertEqual(check_labels[0][1].label_value, 'l2')
        self.assertEqual(check_labels[1][0].label_value, 'l3')

        self.assertEqual(check_labels[0][0].milliseconds, 1000)
        self.assertEqual(check_labels[0][1].milliseconds, 250)
        self.assertEqual(check_labels[1][0].milliseconds, 0)

import os
from unittest.mock import patch

from flask import Flask
from flask_testing import TestCase
from pyfakefs.fake_filesystem_unittest import TestCaseMixin

import backend
import sampling
import sessions
from backend import ImageSlice, SliceType
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

    def test_get_slices_from_session_categorical_slice(self):
        dataset = backend.get_dataset('dataset1')
        slices = [
            ImageSlice('img1.nii.gz', 0, SliceType.SAGITTAL),
            ImageSlice('img1.nii.gz', 100, SliceType.SAGITTAL),
            ImageSlice('img2.nii', 1, SliceType.CORONAL),
            ImageSlice('img3', 255, SliceType.AXIAL)
        ]
        sessions.create_categorical_slice_session(db.session, 'session1', 'prompt', dataset, ['l1', 'l2', 'l3'], slices)
        label_session = sessions.get_session_by_id(db.session, 1)

        check_slices = sampling.get_slices_from_session(label_session)
        self.assertEqual(check_slices, slices)

    def test_get_slices_from_session_comparison_slice(self):
        dataset = backend.get_dataset('dataset1')
        slices = [
            ImageSlice('img1.nii.gz', 0, SliceType.SAGITTAL),
            ImageSlice('img1.nii.gz', 100, SliceType.SAGITTAL),
            ImageSlice('img2.nii', 1, SliceType.CORONAL),
            ImageSlice('img3', 255, SliceType.AXIAL)
        ]
        comparisons = [
            (slices[0], slices[1]),
            (slices[2], slices[0]),
            (slices[3], slices[1])
        ]
        sessions.create_comparison_slice_session(db.session, 'session1', 'prompt', dataset,
                                                 ['l1', 'l2', 'l3'], comparisons)
        label_session = sessions.get_session_by_id(db.session, 1)
        check_slices = sampling.get_slices_from_session(label_session)

        # Note: Result from get_slices_by_session is sorted, so this relies on slices being defined in order above
        self.assertEqual(check_slices, slices)

    def test_get_slices_from_session_invalid_type(self):
        dataset = backend.get_dataset('dataset1')
        sessions.create_categorical_image_session(db.session, 'session1', 'prompt', dataset, ['l1', 'l2', 'l3'])
        label_session = sessions.get_session_by_id(db.session, 1)

        with self.assertRaises(AssertionError):
            sampling.get_slices_from_session(label_session)

    def test_get_comparisons_from_session(self):
        dataset = backend.get_dataset('dataset1')
        slices = [
            ImageSlice('img1.nii.gz', 0, SliceType.SAGITTAL),
            ImageSlice('img1.nii.gz', 100, SliceType.SAGITTAL),
            ImageSlice('img2.nii', 1, SliceType.CORONAL),
            ImageSlice('img3', 255, SliceType.AXIAL)
        ]
        comparisons = [
            (slices[0], slices[1]),
            (slices[2], slices[0]),
            (slices[3], slices[1])
        ]
        sessions.create_comparison_slice_session(db.session, 'session1', 'prompt', dataset,
                                                 ['l1', 'l2', 'l3'], comparisons)
        label_session = sessions.get_session_by_id(db.session, 1)

        check_comparisons = sampling.get_comparisons_from_session(label_session)
        self.assertEqual(check_comparisons, comparisons)

    @patch('sampling.get_volume_width', lambda image_path, slice_type: 256)
    def test_sample_slices_no_duplicates(self):
        dataset = backend.get_dataset('dataset1')
        slices = sampling.sample_slices(dataset, SliceType.SAGITTAL, 2, 100, 10, 90)

        self.assertEqual(len(slices), len(set(slices)))

    def test_sample_comparisons_length(self):
        slices = [
            ImageSlice('img1.nii.gz', 0, SliceType.SAGITTAL),
            ImageSlice('img1.nii.gz', 100, SliceType.SAGITTAL),
            ImageSlice('img2.nii', 1, SliceType.CORONAL),
            ImageSlice('img3', 255, SliceType.AXIAL)
        ]
        comparisons = sampling.sample_comparisons(slices, 3, None)

        comparison_count = len(comparisons)
        self.assertEqual(comparison_count, 3)

    def test_sample_comparisons_self_compare(self):
        slices = [
            ImageSlice('img1.nii.gz', 0, SliceType.SAGITTAL),
            ImageSlice('img1.nii.gz', 100, SliceType.SAGITTAL),
            ImageSlice('img2.nii', 1, SliceType.CORONAL),
            ImageSlice('img3', 255, SliceType.AXIAL)
        ]
        comparisons = sampling.sample_comparisons(slices, 3, None)

        for co in comparisons:
            self.assertNotEqual(co[0], co[1])

    def test_sample_comparisons_max_not_enough(self):
        slices = [
            ImageSlice('img1.nii.gz', 0, SliceType.SAGITTAL),
            ImageSlice('img1.nii.gz', 100, SliceType.SAGITTAL),
            ImageSlice('img2.nii', 1, SliceType.CORONAL),
            ImageSlice('img3', 255, SliceType.AXIAL)
        ]

        with self.assertRaises(AssertionError):
            comparisons = sampling.sample_comparisons(slices, 100, 2)

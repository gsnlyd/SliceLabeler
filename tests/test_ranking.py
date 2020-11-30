import os

from flask import Flask
from flask_testing import TestCase
from pyfakefs.fake_filesystem_unittest import TestCaseMixin

import backend
import ranking
import sampling
from backend import ImageSlice, SliceType
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

    def test_get_ranking_contains_slices(self):
        dataset = backend.get_dataset('dataset1')
        comparisons = [
            (ImageSlice('img1.nii.gz', 0, SliceType.SAGITTAL), ImageSlice('img3', 1, SliceType.CORONAL)),
            (ImageSlice('img2.nii', 0, SliceType.SAGITTAL), ImageSlice('img3', 1, SliceType.AXIAL)),
            (ImageSlice('img2.nii', 255, SliceType.CORONAL), ImageSlice('img1.nii.gz', 100, SliceType.AXIAL))
        ]
        sessions.create_comparison_slice_session(db.session, 'session1', 'prompt', dataset,
                                                 ['l1', 'l2'], comparisons)
        label_session = sessions.get_session_by_id(db.session, 1)

        rank_results = ranking.rank_slices(label_session)
        check_slices = sampling.get_slices_from_session(label_session)

        ranked_slices = [t[0] for t in rank_results]
        self.assertEqual(set(ranked_slices), set(check_slices))

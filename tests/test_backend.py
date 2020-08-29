import os

from pyfakefs.fake_filesystem_unittest import TestCase

import backend


class TestDatasets(TestCase):
    def setUp(self):
        self.setUpPyfakefs()

        self.fs.create_dir(backend.DATASETS_PATH)

        self.fs.create_file(os.path.join(backend.DATASETS_PATH, 'dataset1', 'img1.nii.gz'))
        self.fs.create_file(os.path.join(backend.DATASETS_PATH, 'dataset1', 'img2.nii'))
        self.fs.create_dir(os.path.join(backend.DATASETS_PATH, 'dataset1', 'img3'))

        self.fs.create_file(os.path.join(backend.DATASETS_PATH, 'dataset1', 'abc.jpg'))
        self.fs.create_file(os.path.join(backend.DATASETS_PATH, 'dataset1', '.dotfile'))

        self.fs.create_dir(os.path.join(backend.DATASETS_PATH, 'dataset2'))
        self.fs.create_dir(os.path.join(backend.DATASETS_PATH, 'dataset3'))

    def test_get_datasets_length(self):
        datasets = backend.get_datasets()
        num_datasets = len(datasets)

        self.assertEqual(num_datasets, 3)

    def test_get_datasets_names(self):
        datasets = backend.get_datasets()

        self.assertEqual(datasets[0].name, 'dataset1')
        self.assertEqual(datasets[1].name, 'dataset2')
        self.assertEqual(datasets[2].name, 'dataset3')

    def test_get_datasets_paths(self):
        datasets = backend.get_datasets()

        self.assertEqual(datasets[0].path, os.path.join(backend.DATASETS_PATH, 'dataset1'))
        self.assertEqual(datasets[1].path, os.path.join(backend.DATASETS_PATH, 'dataset2'))
        self.assertEqual(datasets[2].path, os.path.join(backend.DATASETS_PATH, 'dataset3'))

    def test_get_dataset_name(self):
        dataset = backend.get_dataset('dataset1')
        self.assertEqual(dataset.name, 'dataset1')

    def test_get_dataset_path(self):
        dataset = backend.get_dataset('dataset1')
        self.assertEqual(dataset.path, os.path.join(backend.DATASETS_PATH, 'dataset1'))

    def test_get_dataset_non_existent(self):
        non_existent_dataset = backend.get_dataset('dataset_non_existent')
        self.assertIsNone(non_existent_dataset)

    def test_is_image_path(self):
        dataset_path = os.path.join(backend.DATASETS_PATH, 'dataset1')

        self.assertTrue(backend.is_image_path(os.path.join(dataset_path, 'img1.nii.gz')))
        self.assertTrue(backend.is_image_path(os.path.join(dataset_path, 'img2.nii')))
        self.assertTrue(backend.is_image_path(os.path.join(dataset_path, 'img3')))

        self.assertFalse(backend.is_image_path(os.path.join(dataset_path, 'abc.jpg')))
        self.assertFalse(backend.is_image_path(os.path.join(dataset_path, '.dotfile')))

    def test_get_images_length(self):
        dataset = backend.get_dataset('dataset1')
        images = backend.get_images(dataset)
        num_images = len(images)

        self.assertEqual(num_images, 3)

    def test_get_images_datasets(self):
        dataset = backend.get_dataset('dataset1')
        images = backend.get_images(dataset)

        self.assertEqual(images[0].dataset, dataset)
        self.assertEqual(images[1].dataset, dataset)
        self.assertEqual(images[2].dataset, dataset)

    def test_get_images_names(self):
        dataset = backend.get_dataset('dataset1')
        images = backend.get_images(dataset)

        self.assertEqual(images[0].name, 'img1.nii.gz')
        self.assertEqual(images[1].name, 'img2.nii')
        self.assertEqual(images[2].name, 'img3')

    def test_get_images_paths(self):
        dataset = backend.get_dataset('dataset1')
        images = backend.get_images(dataset)

        self.assertEqual(images[0].path, os.path.join(backend.DATASETS_PATH, 'dataset1', 'img1.nii.gz'))
        self.assertEqual(images[1].path, os.path.join(backend.DATASETS_PATH, 'dataset1', 'img2.nii'))
        self.assertEqual(images[2].path, os.path.join(backend.DATASETS_PATH, 'dataset1', 'img3'))

    def test_get_image_dataset(self):
        dataset = backend.get_dataset('dataset1')
        image = backend.get_image(dataset, 'img1.nii.gz')

        self.assertEqual(image.dataset, dataset)

    def test_get_image_name(self):
        dataset = backend.get_dataset('dataset1')
        image = backend.get_image(dataset, 'img1.nii.gz')

        self.assertEqual(image.name, 'img1.nii.gz')

    def test_get_image_path(self):
        dataset = backend.get_dataset('dataset1')
        image = backend.get_image(dataset, 'img1.nii.gz')

        self.assertEqual(image.path, os.path.join(backend.DATASETS_PATH, 'dataset1', 'img1.nii.gz'))

    def test_get_image_non_existent(self):
        dataset = backend.get_dataset('dataset1')

        with self.assertRaises(AssertionError):
            backend.get_image(dataset, 'non_existent_image.nii.gz')

    def test_get_image_by_index_image_count(self):
        dataset = backend.get_dataset('dataset1')
        image, num_images = backend.get_image_by_index(dataset, 0)

        self.assertEqual(num_images, 3)

    def test_get_image_by_index_image_count_empty(self):
        dataset = backend.get_dataset('dataset2')
        image, num_images = backend.get_image_by_index(dataset, 0)

        self.assertEqual(num_images, 0)

    def test_get_image_by_index_dataset(self):
        dataset = backend.get_dataset('dataset1')
        image, num_images = backend.get_image_by_index(dataset, 0)

        self.assertEqual(image.dataset, dataset)

    def test_get_image_by_index_name(self):
        dataset = backend.get_dataset('dataset1')
        image, num_images = backend.get_image_by_index(dataset, 0)

        self.assertEqual(image.name, 'img1.nii.gz')

    def test_get_image_by_index_path(self):
        dataset = backend.get_dataset('dataset1')
        image, num_images = backend.get_image_by_index(dataset, 0)

        self.assertEqual(image.path, os.path.join(backend.DATASETS_PATH, 'dataset1', 'img1.nii.gz'))

    def test_get_image_by_index_out_of_bounds_lower(self):
        dataset = backend.get_dataset('dataset1')
        image, num_images = backend.get_image_by_index(dataset, -1)

        self.assertIsNone(image)

    def test_get_image_by_index_out_of_bounds_upper(self):
        dataset = backend.get_dataset('dataset1')
        image, num_images = backend.get_image_by_index(dataset, 3)

        self.assertIsNone(image)


class TestDatasetsEmpty(TestCase):
    def setUp(self):
        self.setUpPyfakefs()
        self.fs.create_dir(backend.DATASETS_PATH)

    def test_get_datasets_empty(self):
        datasets = backend.get_datasets()
        num_datasets = len(datasets)

        self.assertEqual(num_datasets, 0)

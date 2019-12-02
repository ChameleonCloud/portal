from django.test import TestCase
from unittest import mock

from .. import DEV as dev
from jupyterlab_zenodo.zenodo import ZenodoClient
from jupyterlab_zenodo.utils import get_zenodo_file_link


@mock.patch('sharing_portal.utils.dev', False)
class GetZenodoFileLinkTest(TestCase):
    def setUp(self):
        self.old_rec_id = '1205167'
        self.old_file_link = ('record/3267438/files/go-release-archive.tgz')
        self.current_rec_id = '3269114'
        self.current_file_link = ('record/3269114/files/figure.png')

    def test_get_files_old_version(self):
        link = get_zenodo_file_link(self.old_rec_id)
        self.assertEqual(link, self.old_file_link)

    def test_get_files_current_version(self):
        link = get_zenodo_file_link(self.current_rec_id)
        self.assertEqual(link, self.current_file_link)


@mock.patch('sharing_portal.utils.dev', True)
class GetZenodoFileLinkTest_Dev(TestCase):
    def setUp(self):
        self.old_rec_id = '359090'
        self.old_file_link = ('record/359091/files/new-title.zip')
        self.current_rec_id = '359165'
        self.current_file_link = ('record/359165/files/some-title.zip')

    def test_get_files_old_version_dev(self):
        link = get_zenodo_file_link(self.old_rec_id)
        self.assertEqual(link, self.old_file_link)

    def test_get_files_current_version_dev(self):
        link = get_zenodo_file_link(self.current_rec_id)
        self.assertEqual(link, self.current_file_link)


class GetRecIdTest(TestCase):
    def test_good_doi(self):
        self.assertEqual(ZenodoClient.to_record('10.5281/zenodo.3357455'), '3357455')

    def test_invalid_doi(self):
        with self.assertRaises(Exception):
            ZenodoClient.to_record('notadoi')

    def test_num_invalid_doi(self):
        with self.assertRaises(Exception):
            ZenodoClient.to_record('127381273')

    def test_non_zenodo_doi(self):
        with self.assertRaises(Exception):
            ZenodoClient.to_record('11111/notzenodo.123123')

    def test_empty_doi(self):
        with self.assertRaises(Exception):
            ZenodoClient.to_record('')

    def test_no_doi(self):
        with self.assertRaises(Exception):
            ZenodoClient.to_record(None)

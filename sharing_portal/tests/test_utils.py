from django.test import TestCase
from unittest import mock

from ..__init__ import DEV as dev
from ..utils import get_rec_id, get_permanent_id, get_zenodo_file_link


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


@mock.patch('sharing_portal.utils.dev', False)
class GetPermanentIdTest(TestCase):
    def setUp(self):
        self.old_version_id = '1205167'
        self.old_version_perm = '1205166'
        self.only_version_id = '3269114'
        self.only_version_perm = '3269113'

    @mock.patch('sharing_portal.utils.get_rec_id')
    def test_get_permanent_id_old_version(self, mock_id):
        mock_id.return_value = self.old_version_id
        self.assertEqual(self.old_version_perm, get_permanent_id("doi"))

    @mock.patch('sharing_portal.utils.get_rec_id')
    def test_get_permanent_id_current_version(self, mock_id):
        mock_id.return_value = self.only_version_id
        self.assertEqual(self.only_version_perm, get_permanent_id("doi"))


@mock.patch('sharing_portal.utils.dev', True)
class GetPermanentId_DevTest(TestCase):
    def setUp(self):
        self.old_version_id = '359090'
        self.old_version_perm = '359089'
        self.only_version_id = '359165'
        self.only_version_perm = '359164'

    @mock.patch('sharing_portal.utils.get_rec_id')
    def test_get_permanent_id_old_version_dev(self, mock_id):
        mock_id.return_value = self.old_version_id
        self.assertEqual(self.old_version_perm, get_permanent_id("doi"))

    @mock.patch('sharing_portal.utils.get_rec_id')
    def test_get_permanent_id_current_version_dev(self, mock_id):
        mock_id.return_value = self.only_version_id
        self.assertEqual(self.only_version_perm, get_permanent_id("doi"))

    @mock.patch('sharing_portal.utils.get_rec_id')
    def test_bad_id_dev(self, mock_id):
        mock_id.return_value = "notanid"
        with self.assertRaises(Exception):
            get_permanent_id("doi")


class GetRecIdTest(TestCase):
    def test_good_doi(self):
        dep_id = get_rec_id('10.5281/zenodo.3357455')
        self.assertEqual(dep_id, '3357455')

    def test_invalid_doi(self):
        with self.assertRaises(Exception):
            get_rec_id('notadoi')

    def test_num_invalid_doi(self):
        with self.assertRaises(Exception):
            get_rec_id('127381273')

    def test_non_zenodo_doi(self):
        with self.assertRaises(Exception):
            get_rec_id('11111/notzenodo.123123')

    def test_empty_doi(self):
        with self.assertRaises(Exception):
            get_rec_id('')

    def test_no_doi(self):
        with self.assertRaises(Exception):
            get_rec_id(None)
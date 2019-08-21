from datetime import datetime
import unittest
from unittest import mock

from django.core.exceptions import ValidationError

from .__init__ import DEV as dev
from .models import Artifact, Author, Label
from .utils import get_rec_id

# Create your tests here.

'''
class searchFailure(TestCase):
    c = Client()
    response = c.post('/portal/',{'
    def search_raies_exception(self):
'''

"""
Tests for utils.py
"""

class TestTrue(unittest.TestCase):
    def test_True(self):
        self.assertTrue(True)

class GetRecIdTest(unittest.TestCase):
    def test_good_doi(self):
        dep_id = get_rec_id('10.5281/zenodo.3357455')
        self.assertEqual(dep_id, '3357455')

    def invalid_doi(self):
        with self.assertRaises(Exception):
            get_rec_id('notadoi')

    def num_invalid_doi(self):
        with self.assertRaises(Exception):
            get_rec_id('127381273')

    def non_zenodo_doi(self):
        with self.assertRaises(Exception):
            get_rec_id('11111/notzenodo.123123')

    def test_empty_doi(self):
        with self.assertRaises(Exception):
            get_rec_id('')

    def test_no_doi(self):
        with self.assertRaises(Exception):
            get_rec_id(None)


"""
Tests for models
"""

class ArtifactImageFilenameTest(unittest.TestCase):
    def setUp(self):
        now = datetime.now()
        self.a = Artifact.objects.create(
                    title='Test Case Artifact a',
                    created_at=now,
                    updated_at=now,
        )
    def test_normal_name(self):
        self.a.image = 'directory/name.png'
        self.assertEqual(self.a.image_filename(), 'name.png')

    def test_no_dir(self):
        self.a.image = 'name.png'
        self.assertEqual(self.a.image_filename(), 'name.png')

    def test_no_image(self):
        self.assertEqual(self.a.image_filename(), None)

class ArtifactRelatedPapersTest(unittest.TestCase):
    def setUp(self):
        now = datetime.now()
        self.a = Artifact.objects.create(
                    title='Test Case Artifact a',
                    created_at=now,
                    updated_at=now,
        )    
        self.b = Artifact.objects.create(
                    title='Test Case Artifact b',
                    created_at=now,
                    updated_at=now,
        )
        self.c = Artifact.objects.create(
                    title='Test Case Artifact c',
                    created_at=now,
                    updated_at=now,
        )
        self.label1 = Label.objects.create(label="label1")
        self.label2 = Label.objects.create(label="label2")
        self.label3 = Label.objects.create(label="label3")
    def test_multiple_shared_labels(self):
        llist = [self.label1, self.label2, self.label3] 
        self.a.labels.set(llist)
        self.b.labels.set(llist)
        self.c.labels.set(llist)
        related = self.a.related_papers()
        self.assertEqual(len(related),2)
        self.assertEqual([a.id for a in related].sort(),
                         [self.b.id, self.c.id].sort())

    def test_different_shared_labels(self):
        llist = [self.label1, self.label2, self.label3] 
        self.a.labels.set(llist)
        self.b.labels.set([self.label2])
        self.c.labels.set([self.label3])
        related = self.a.related_papers()
        self.assertEqual(len(related),2)
        self.assertEqual([a.id for a in related].sort(),
                         [self.b.id, self.c.id].sort())

    def test_some_not_shared(self):
        llist = [self.label1, self.label2] 
        self.a.labels.set(llist)
        self.b.labels.set([self.label2])
        self.c.labels.set([self.label3])
        related = self.a.related_papers()
        self.assertEqual(len(related),1)
        self.assertEqual([a.id for a in related].sort(),
                         [self.b.id].sort())

    def test_no_related(self):
        llist = [self.label1, self.label2] 
        self.a.labels.set([self.label3])
        self.b.labels.set(llist)
        self.c.labels.set(llist)
        related = self.a.related_papers()
        self.assertEqual(len(related),0)

@mock.patch('sharing.models.get_zenodo_file_link')
@mock.patch('sharing.models.get_rec_id')
class ArtifactJupyterHubLinkTest(unittest.TestCase):
    def setUp(self):
        self.the_id = '1234'
        self.the_link = 'file_link'
        if dev:
            self.hub = "http://localhost:8000"
        else:
            self.hub = "https://jupyter.chameleoncloud.org"
        now = datetime.now()
        self.a = Artifact.objects.create(
                    title='Test Case Artifact',
                    image='place/image.png',
                    created_at=now,
                    updated_at=now,
        )
    def test_has_both(self, mock_id, mock_link):
        mock_id.return_value = self.the_id
        mock_link.return_value = self.the_link
        self.a.doi='10.1112/zenodo.22222'
        self.a.git_repo='account/repo'
        jhl = self.a.jupyterhub_link()
        self.assertEqual(jhl, self.hub+("/hub/import?source=git&src_path="
                                        "account/repo.git"))

    def test_just_git(self, mock_id, mock_link):
        mock_id.return_value = self.the_id
        mock_link.return_value = self.the_link
        self.a.doi='10.1112/zenodo.22222'

@mock.patch('sharing.models.get_zenodo_file_link')
@mock.patch('sharing.models.get_rec_id')
class ArtifactJupyterHubLinkTest(unittest.TestCase):
    def setUp(self):
        self.the_id = '1234'
        self.the_link = 'file_link'
        if dev:
            self.hub = "http://localhost:8000"
        else:
            self.hub = "https://jupyter.chameleoncloud.org"
        now = datetime.now()
        self.a = Artifact.objects.create(
                    title='Test Case Artifact',
                    image='place/image.png',
                    created_at=now,
                    updated_at=now,
        )
    def test_has_both(self, mock_id, mock_link):
        mock_id.return_value = self.the_id
        mock_link.return_value = self.the_link
        self.a.doi='10.1112/zenodo.22222'
        self.a.git_repo='account/repo'
        jhl = self.a.jupyterhub_link()
        self.assertEqual(jhl, self.hub+("/hub/import?source=git&src_path="
                                        "account/repo.git"))

    def test_just_git(self, mock_id, mock_link):
        mock_id.return_value = self.the_id
        mock_link.return_value = self.the_link
        self.a.doi='10.1112/zenodo.22222'
        self.a.git_repo='account/repo'
        jhl = self.a.jupyterhub_link()
        self.assertEqual(jhl, self.hub+("/hub/import?source=git&src_path="
                                        "account/repo.git"))

    def test_just_zenodo(self, mock_id, mock_link):
        mock_id.return_value = self.the_id
        mock_link.return_value = self.the_link
        self.a.doi='10.1112/zenodo.22222'
        jhl = self.a.jupyterhub_link()
        self.assertEqual(jhl, self.hub+("/hub/import?source=zenodo&src_path="
                                        "file_link"))

    def test_none(self, mock_id, mock_link):
        mock_id.return_value = self.the_id
        mock_link.return_value = self.the_link
        with self.assertRaises(Exception):
            jhl = self.a.jupyterhub_link()


class ArtifactZenodoLinkTest(unittest.TestCase):
    def setUp(self):
        if dev:
            self.base = "https://sandbox.zenodo.org/record/"
        else:
            self.base = "https://zenodo.org/record/"

        now = datetime.now()
        self.a = Artifact.objects.create(
                    title='Test Case Artifact',
                    image='place/image.png',
                    created_at=now,
                    updated_at=now,
                    doi='10.1112/zenodo.22222',
                    git_repo='account/repo'
        )
    def test_existing_perm_id(self):
        self.a.permanent_id = "22221" 
        link = self.a.zenodo_link()
        self.assertEqual(self.base+self.a.permanent_id, link)
        
    @mock.patch('sharing.models.get_permanent_id')
    def test_no_perm_id(self, mock_perm_id):
        mock_perm_id.return_value = "12345"
        link = self.a.zenodo_link()
        self.assertEqual(self.base+"12345", link)

class ArtifactValidateZenodoDoiTest(unittest.TestCase):
    def test_good_doi(self):
        doi='10.1112/zenodo.22222'
        Artifact.validate_zenodo_doi(doi)

    def test_none(self):
        doi = None
        with self.assertRaises(ValidationError):
            Artifact.validate_zenodo_doi(doi)

    def test_empty(self):
        doi = ''
        with self.assertRaises(ValidationError):
            Artifact.validate_zenodo_doi(doi)

    def test_not_a_doi(self):
        doi = 'somerandomthing'
        with self.assertRaises(ValidationError):
            Artifact.validate_zenodo_doi(doi)

    def test_not_a_zenodo_doi(self):
        doi = '12.312/something.278912'
        with self.assertRaises(ValidationError):
            Artifact.validate_zenodo_doi(doi)

    def test_punctuated_non_doi(self):
        doi = 'aa.aaaa/23423.sghwe'
        with self.assertRaises(ValidationError):
            Artifact.validate_zenodo_doi(doi)


class Validate_Zenodo_Doi_Test(unittest.TestCase):
    def test_good_repo(self):
        Artifact.validate_git_repo("something/something-else")

    def test_no_repo(self):
        with self.assertRaises(ValidationError):
            Artifact.validate_git_repo(None)

    def test_empty_repo(self):
        with self.assertRaises(ValidationError):
            Artifact.validate_git_repo('')

    def test_spaced_repo(self):
        with self.assertRaises(ValidationError):
            Artifact.validate_git_repo('this has spaces')

    def test_noslash_repo(self):
        with self.assertRaises(ValidationError):
            Artifact.validate_git_repo('thishasnoslash')

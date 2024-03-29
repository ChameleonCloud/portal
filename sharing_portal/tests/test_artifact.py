from datetime import datetime
from django.test import TestCase
from unittest import mock

from django.core.exceptions import ValidationError

from .. import DEV as dev
from ..models import Artifact, Label


class ArtifactStringTest(TestCase):
    def test_to_string(self):
        now = datetime.now()
        self.a = Artifact.objects.create(
            title="Test Case Artifact a",
            created_at=now,
            updated_at=now,
        )
        self.assertEqual(str(self.a), self.a.title)


class ArtifactRelatedPapersTest(TestCase):
    def setUp(self):
        now = datetime.now()
        self.a = Artifact.objects.create(
            title="Test Case Artifact a",
            created_at=now,
            updated_at=now,
        )
        self.b = Artifact.objects.create(
            title="Test Case Artifact b",
            created_at=now,
            updated_at=now,
        )
        self.c = Artifact.objects.create(
            title="Test Case Artifact c",
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
        related = self.a.related_papers
        self.assertEqual(len(related), 2)
        self.assertEqual([a.id for a in related].sort(), [self.b.id, self.c.id].sort())

    def test_different_shared_labels(self):
        llist = [self.label1, self.label2, self.label3]
        self.a.labels.set(llist)
        self.b.labels.set([self.label2])
        self.c.labels.set([self.label3])
        related = self.a.related_papers
        self.assertEqual(len(related), 2)
        self.assertEqual([a.id for a in related].sort(), [self.b.id, self.c.id].sort())

    def test_some_not_shared(self):
        llist = [self.label1, self.label2]
        self.a.labels.set(llist)
        self.b.labels.set([self.label2])
        self.c.labels.set([self.label3])
        related = self.a.related_papers
        self.assertEqual(len(related), 1)
        self.assertEqual([a.id for a in related].sort(), [self.b.id].sort())

    def test_no_related(self):
        llist = [self.label1, self.label2]
        self.a.labels.set([self.label3])
        self.b.labels.set(llist)
        self.c.labels.set(llist)
        related = self.a.related_papers
        self.assertEqual(len(related), 0)


class ArtifactValidateZenodoDoiTest(TestCase):
    def test_good_doi(self):
        doi = "10.1112/zenodo.22222"
        Artifact.validate_zenodo_doi(doi)

    def test_none(self):
        doi = None
        with self.assertRaises(ValidationError):
            Artifact.validate_zenodo_doi(doi)

    def test_empty(self):
        doi = ""
        with self.assertRaises(ValidationError):
            Artifact.validate_zenodo_doi(doi)

    def test_not_a_doi(self):
        doi = "somerandomthing"
        with self.assertRaises(ValidationError):
            Artifact.validate_zenodo_doi(doi)

    def test_not_a_zenodo_doi(self):
        doi = "12.312/something.278912"
        with self.assertRaises(ValidationError):
            Artifact.validate_zenodo_doi(doi)

    def test_punctuated_non_doi(self):
        doi = "aa.aaaa/23423.sghwe"
        with self.assertRaises(ValidationError):
            Artifact.validate_zenodo_doi(doi)


class Validate_Zenodo_Doi_Test(TestCase):
    def test_good_repo(self):
        Artifact.validate_git_repo("something/something-else")

    def test_no_repo(self):
        with self.assertRaises(ValidationError):
            Artifact.validate_git_repo(None)

    def test_empty_repo(self):
        with self.assertRaises(ValidationError):
            Artifact.validate_git_repo("")

    def test_spaced_repo(self):
        with self.assertRaises(ValidationError):
            Artifact.validate_git_repo("this has spaces")

    def test_noslash_repo(self):
        with self.assertRaises(ValidationError):
            Artifact.validate_git_repo("thishasnoslash")

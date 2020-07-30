from datetime import datetime
from unittest import mock

from django.test import TestCase
from django.urls import reverse

from ..models import Artifact, Author, Label
from ..views import make_author, upload_artifact


def sorted_list_ids(alist):
    """
    Helper function to turn a list of items into a sorted list of ids
    """
    new_list = list(map(lambda x: x.id, list(alist)))
    new_list.sort()
    return new_list


class UploadViewTest(TestCase):
    def test_no_doi_get(self):
        # If there's no doi gracefully redirect with error
        error_message = ("No doi was provided. To upload to the portal,"
                         " include a Zenodo DOI as a query argument")
        url = reverse('upload')
        response = self.client.get(url, follow=True)
        message = list(response.context.get('messages'))[0]
        self.assertRedirects(response, reverse('index'), status_code=302,
                             target_status_code=200, msg_prefix='',
                             fetch_redirect_response=True)
        self.assertIn(error_message, message.message)

    @mock.patch('sharing_portal.views.upload_artifact')
    def test_no_deposition_with_doi(self, mock_upload):
        # If there's no relevant deposition, gracefully redirect with error
        error_message = "There is no Zenodo publication with that DOI"
        mock_upload.return_value = None
        url = reverse('upload')
        url += "?doi=a.d/o.i"
        response = self.client.get(url, follow=True)
        message = list(response.context.get('messages'))[0]
        self.assertRedirects(response, reverse('index'), status_code=302,
                             target_status_code=200, msg_prefix='',
                             fetch_redirect_response=True)
        self.assertIn(error_message, message.message)

    @mock.patch('sharing_portal.views.upload_artifact')
    def test_success(self, mock_upload):
        # A successful upload should cause a redirect to the detail page
        now = datetime.now()
        a = Artifact(
            title='Test Title',
            created_at=now,
            updated_at=now,
        )
        a.save()
        mock_upload.return_value = a.pk
        url = reverse('upload')
        url += "?doi=a.d/o.i"
        response = self.client.get(url, follow=True)
        redirect_url = reverse('detail', args=(a.pk,))
        self.assertRedirects(response, redirect_url, status_code=302,
                             target_status_code=200, msg_prefix='',
                             fetch_redirect_response=True)


class UploadArtifactTest(TestCase):
    def setUp(self):
        self.doi = '10.1112/zenodo.22222'

    # For the purpose of these tests, put all names
    # into first_name for each author
    def make_simple_author(name_string):
        a = Author(title='', first_name=name_string, last_name='')
        a.save()
        return a.pk

    @mock.patch('sharing_portal.views.dev', True)
    @mock.patch('sharing_portal.views.make_author', make_simple_author)
    def test_dev_success(self):
        pk = upload_artifact(self.doi)
        artifact = Artifact.objects.get(pk=pk)
        self.assertEqual(artifact.title, "Sample Title")
        self.assertEqual(artifact.description, "This is a description")
        self.assertEqual(len(list(artifact.authors.all())), 1)
        self.assertEqual(artifact.authors.all()[0].first_name, "Some Name")

    @mock.patch('sharing_portal.views.dev', False)
    @mock.patch('sharing_portal.views.make_author', make_simple_author)
    def test_non_dev_success(self):
        pk = upload_artifact(self.doi)
        artifact = Artifact.objects.get(pk=pk)
        self.assertEqual(artifact.title,  ("Modelling and Simulation of Water"
                                           " Networks based on Loop Method"))
        self.assertIn("Simulator algorithm for water networks",
                      artifact.description)
        self.assertEqual(len(list(artifact.authors.all())), 1)
        self.assertEqual(artifact.authors.all()[0].first_name,
                         "Arsene, Corneliu")

    @mock.patch('sharing_portal.views.dev', True)
    @mock.patch('sharing_portal.views.make_author', make_simple_author)
    def test_failed_request(self):
        # Should fail gracefully when given a bad id
        pk = upload_artifact(self.doi)
        self.assertIsNone(pk)

    @mock.patch('sharing_portal.views.dev', True)
    @mock.patch('sharing_portal.views.make_author', make_simple_author)
    def test_dev_multiple_authors(self, mock_id):
        mock_id.return_value = "361531"
        pk = upload_artifact(self.doi)
        artifact = Artifact.objects.get(pk=pk)
        self.assertEqual(artifact.title, "A title")
        self.assertEqual(artifact.description, "A thing")
        self.assertEqual(len(artifact.authors.all()), 2)
        self.assertEqual(artifact.authors.all()[0].first_name, "A person")
        self.assertEqual(artifact.authors.all()[1].first_name, "Second person")


class MakeAuthorTest(TestCase):
    def test_title_fname_lname(self):
        author_str = "Dr. Albert Einstein"
        author_pk = make_author(author_str)
        a = Author.objects.get(pk=author_pk)
        self.assertEqual(a.title, "Dr.")
        self.assertEqual(a.first_name, "Albert")
        self.assertEqual(a.last_name, "Einstein")

    def test_simple_with_comma(self):
        author_str = "Skywalker, Luke"
        author_pk = make_author(author_str)
        a = Author.objects.get(pk=author_pk)
        self.assertEqual(a.title, '')
        self.assertEqual(a.first_name, "Luke")
        self.assertEqual(a.last_name, "Skywalker")

    def test_multiple_with_comma(self):
        author_str = "Potter, Harry James"
        author_pk = make_author(author_str)
        a = Author.objects.get(pk=author_pk)
        self.assertEqual(a.title, '')
        self.assertEqual(a.first_name, "Harry James")
        self.assertEqual(a.last_name, "Potter")

    def test_five_names(self):
        author_str = "Adam Albert John Jacob Samuels"
        author_pk = make_author(author_str)
        a = Author.objects.get(pk=author_pk)
        self.assertEqual(a.title, '')
        self.assertEqual(a.first_name, author_str)
        self.assertEqual(a.last_name, '')

    def test_fname_lname(self):
        author_str = "Fred Astaire"
        author_pk = make_author(author_str)
        a = Author.objects.get(pk=author_pk)
        self.assertEqual(a.title, '')
        self.assertEqual(a.first_name, "Fred")
        self.assertEqual(a.last_name, "Astaire")

    def test_three_names_no_title(self):
        author_str = "Sir Isaac Newton"
        author_pk = make_author(author_str)
        a = Author.objects.get(pk=author_pk)
        self.assertEqual(a.title, '')
        self.assertEqual(a.first_name, "Sir Isaac")
        self.assertEqual(a.last_name, "Newton")

    def test_one_name(self):
        author_str = "Sting"
        author_pk = make_author(author_str)
        a = Author.objects.get(pk=author_pk)
        self.assertEqual(a.title, '')
        self.assertEqual(a.first_name, "Sting")
        self.assertEqual(a.last_name, '')

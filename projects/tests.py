from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.test import TestCase, modify_settings, override_settings
from django.utils import timezone
import mock
import json

@modify_settings(
    MIDDLEWARE_CLASSES={
        'remove': ['termsandconditions.middleware.TermsAndConditionsRedirectMiddleware',]
    }
)
@override_settings(
    AUTHENTICATION_BACKENDS = ('django.contrib.auth.backends.ModelBackend',)
)
class ProjectViewTests(TestCase):


    def setUp(self):
        user_fixture = json.loads(open('projects/test_fixtures/user.json').read())
        self.test_user = get_user_model().objects.create_user(
                user_fixture['username'],
                user_fixture['email'],
                'password')
        self.test_user.backend = 'tas.auth.TASBackend'

    def test_view_project_redirect(self):
        response = self.client.get(reverse('projects:view_project', args=[1234]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'],
            'http://testserver/login/?next=/user/projects/1234/')

    # Test that a project with an active allocation up for renewal displays the recharge button
    # User is PI
    @mock.patch('pytas.http.TASClient.get_project_users')
    @mock.patch('pytas.http.TASClient.project')
    def test_view_project(self, mock_tasclient_project, mock_tasclient_project_users):
        projects_fixture = json.loads(
            open('projects/test_fixtures/project_1234.json').read())
        mock_tasclient_project.return_value = projects_fixture

        project_users_fixture = json.loads(
            open('projects/test_fixtures/project_users.json').read())
        mock_tasclient_project_users.return_value = project_users_fixture

        self.client.login(username='jdoe1', password='password')
        response = self.client.get(reverse('projects:view_project', args=[1234]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Chameleon Project Request Test')
        self.assertContains(response,
            'data-allocation-id="1111" data-allocation-status="inactive"')
        self.assertContains(response,
            'data-allocation-id="1112" data-allocation-status="rejected"')
        self.assertContains(response,
            'data-allocation-id="1113" data-allocation-status="active"')
        self.assertContains(response, 'Recharge/extend allocation')

    # Test that a project with an active allocation up for renewal does NOT display the recharge button
    # if there is also a pending allocation
    # User is PI
    @mock.patch('pytas.http.TASClient.get_project_users')
    @mock.patch('pytas.http.TASClient.project')
    def test_view_project_with_pending(self, mock_tasclient_project, mock_tasclient_project_users):
        projects_fixture = json.loads(
            open('projects/test_fixtures/project_1235.json').read())
        mock_tasclient_project.return_value = projects_fixture

        project_users_fixture = json.loads(
            open('projects/test_fixtures/project_users.json').read())
        mock_tasclient_project_users.return_value = project_users_fixture

        self.client.login(username='jdoe1', password='password')
        response = self.client.get(reverse('projects:view_project', args=[1235]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Chameleon Project Request Test')
        self.assertContains(response,
            'data-allocation-id="1114" data-allocation-status="active"')
        self.assertContains(response,
            'data-allocation-id="1115" data-allocation-status="pending"')
        self.assertNotContains(response, 'Recharge/extend allocation')

    # Test that a project with a rejected allocation displays the resubmit button
    # ONLY if there are no Pending or Active allocations
    # User is PI
    @mock.patch('pytas.http.TASClient.get_project_users')
    @mock.patch('pytas.http.TASClient.project')
    def test_view_allocation_rejected(self, mock_tasclient_project, mock_tasclient_project_users):
        projects_fixture = json.loads(
            open('projects/test_fixtures/project_1236.json').read())
        mock_tasclient_project.return_value = projects_fixture

        project_users_fixture = json.loads(
            open('projects/test_fixtures/project_users.json').read())
        mock_tasclient_project_users.return_value = project_users_fixture

        self.client.login(username='jdoe1', password='password')
        response = self.client.get(reverse('projects:view_project', args=[1236]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Chameleon Project Request Test')
        self.assertContains(response,
            'data-allocation-id="1115" data-allocation-status="inactive"')
        self.assertContains(response,
            'data-allocation-id="1114" data-allocation-status="rejected"')
        self.assertContains(response, 'Resubmit allocation')

    # Test that a project with a rejected allocation DOES NOT display the resubmit button
    # if there are Pending or Active allocations
    # User is PI
    @mock.patch('pytas.http.TASClient.get_project_users')
    @mock.patch('pytas.http.TASClient.project')
    def test_view_allocation_rejected_with_active(self, mock_tasclient_project, mock_tasclient_project_users):
        projects_fixture = json.loads(
            open('projects/test_fixtures/project_1234.json').read())
        mock_tasclient_project.return_value = projects_fixture

        project_users_fixture = json.loads(
            open('projects/test_fixtures/project_users.json').read())
        mock_tasclient_project_users.return_value = project_users_fixture

        self.client.login(username='jdoe1', password='password')
        response = self.client.get(reverse('projects:view_project', args=[1235]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Chameleon Project Request Test')
        self.assertContains(response,
            'data-allocation-id="1113" data-allocation-status="active"')
        self.assertContains(response,
            'data-allocation-id="1111" data-allocation-status="inactive"')
        self.assertContains(response,
            'data-allocation-id="1112" data-allocation-status="rejected"')
        self.assertNotContains(response, 'Resubmit allocation')

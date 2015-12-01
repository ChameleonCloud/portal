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

    user_fixture = json.loads(open('projects/fixtures/user.json').read())
    projects_fixture = json.loads(open('projects/fixtures/user_projects.json').read())

    def setUp(self):
        self.test_user = get_user_model().objects.create_user(
                self.user_fixture['username'],
                self.user_fixture['email'],
                'password')
        self.test_user.backend = 'tas.auth.TASBackend'

    def test_view_project_redirect(self):
        response = self.client.get(reverse('projects:view_project', args=[1234]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'],
            'http://testserver/login/?next=/user/projects/1234/')

    @mock.patch('pytas.http.TASClient.project')
    def test_view_project(self, mock_tasclient_project):
        mock_tasclient_project.return_value = self.projects_fixture

        self.client.login(username='jdoe1', password='password')
        response = self.client.get(reverse('projects:view_project', args=[1234]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Chameleon Project Request Test')
        self.assertContains(response, 'data-allocation-id="1111" data-allocation-status="inactive"')
        self.assertContains(response, 'data-allocation-id="1112" data-allocation-status="rejected"')
        self.assertContains(response, 'data-allocation-id="1113" data-allocation-status="active"')
        self.assertContains(response, 'Recharge/extend allocation')
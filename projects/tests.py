from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.test import TestCase, modify_settings, override_settings
from termsandconditions.models import TermsAndConditions, UserTermsAndConditions
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

    fixtures = ['termsandconditions.json']

    def setUp(self):
        user_fixture = json.loads(open('projects/test_fixtures/user.json').read())
        self.test_user = get_user_model().objects.create_user(
                user_fixture['username'],
                user_fixture['email'],
                'password')
        project_terms = TermsAndConditions.objects.get(slug='project-terms')
        user_terms = UserTermsAndConditions(user=self.test_user, terms=project_terms)
        user_terms.save()

        self.test_user.backend = 'tas.auth.TASBackend'

    def test_view_project_redirect(self):
        response = self.client.get(reverse('projects:view_project', args=[1234]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response['Location'],
            'http://testserver/login/?next=/user/projects/1234/')

    @mock.patch('pytas.http.TASClient.get_project_users')
    @mock.patch('pytas.http.TASClient.project')
    def test_view_project(self, mock_tasclient_project, mock_tasclient_project_users):
        """
        Test that a project with an active allocation up for renewal displays the recharge
        button.

        Precondition: User is PI.
        Args:
            mock_tasclient_project:
            mock_tasclient_project_users:

        Returns:

        """
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

    @mock.patch('pytas.http.TASClient.fields')
    @mock.patch('pytas.http.TASClient.get_user')
    def test_project_form_fields_required(self, mock_tas_get_user, mock_tas_fields):
        """
        Tests that appropriate fields are required on the project form.
        Args:
            mock_tas_get_user:
            mock_tas_fields:

        Returns:

        """
        with open('projects/test_fixtures/fields.json') as f:
            mock_tas_fields.return_value = json.loads(f.read())

        with open('projects/test_fixtures/user.json') as f:
            mock_tas_get_user.return_value = json.loads(f.read())

        self.client.login(username='jdoe1', password='password')
        response = self.client.get(reverse('projects:create_project'))

        self.assertContains(
            response,
            '<textarea class="form-control" cols="40" id="id_supplemental_details" '
            'name="supplemental_details" placeholder="Resource Justification" '
            'required="required" rows="10" title="Provide supplemental detail on how you '
            'intend to use Chameleon to accomplish your research goals. This text will '
            'not be publicly viewable and may include details that you do not wish to '
            'publish.">')

    @mock.patch('pytas.http.TASClient.project')
    @mock.patch('pytas.http.TASClient.fields')
    @mock.patch('pytas.http.TASClient.get_user')
    def test_allocation_form_fields_required(self, mock_tas_get_user, mock_tas_fields, mock_tas_project):
        """
        Tests that appropriate fields are required on the project form.
        Args:
            mock_tas_get_user:
            mock_tas_fields:

        Returns:

        """
        with open('projects/test_fixtures/fields.json') as f:
            mock_tas_fields.return_value = json.loads(f.read())

        with open('projects/test_fixtures/user.json') as f:
            mock_tas_get_user.return_value = json.loads(f.read())

        with open('projects/test_fixtures/project_1234.json') as f:
            mock_tas_project.return_value = json.loads(f.read())

        self.client.login(username='jdoe1', password='password')
        response = self.client.get(
            reverse('projects:renew_allocation', args=(1234, 1113)))

        print(response)

        self.assertContains(
            response,
            '<textarea class="form-control" cols="40" id="id_supplemental_details" '
            'name="supplemental_details" placeholder="Resource Justification" '
            'required="required" rows="10" title="Please provide an update on the use of '
            'your current allocation - any success stories, publications, presentations, '
            'or just a general update on the progress of your research on Chameleon. '
            'This is helpful for us as we communicate with NSF regarding the value '
            'Chameleon is bringing to the research community.">'
            )

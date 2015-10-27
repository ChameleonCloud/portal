from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.test import Client, TestCase
from tas.forms import *
from termsandconditions.models import TermsAndConditions
import mock
import os

def test_user_fixture():
    return {
            "username": "jdoe1",
            "citizenshipId": 230,
            "countryId": 230,
            "citizenship": "United States",
            "firstName": "John",
            "source": "Standard",
            "institutionId": 1,
            "lastName": "Doe",
            "title": "University Research Staff",
            "piEligibility": "Eligible",
            "phone": "555 555 1234",
            "id": 98765,
            "email": "jdoe1@tacc.utexas.edu",
            "departmentId": 127,
            "country": "United States",
            "department": "Department of Computer Science",
            "emailConfirmations": [],
            "institution": "University of Texas at Austin",
            "source": "Chameleon"
            }

def mock_registration_form_data():
    return {
        'firstName': 'John',
        'lastName': 'Doe',
        'email': 'jdoe1@tacc.utexas.edu',
        'institutionId': 1,
        'departmentId': 127,
        'institution': '',
        'title': 'University Research Staff',
        'countryId': 230,
        'citizenshipId': 230,
        'username': 'jdoe1',
        'password': 'asdf;1234;',
        'confirmPassword': 'asdf;1234;'
        }

# Create your tests here.
class RegisterViewTests(TestCase):

    @mock.patch('tas.forms.get_country_choices')
    @mock.patch('tas.forms.get_department_choices')
    @mock.patch('tas.forms.get_institution_choices')
    def test_register_view(self, mock_get_institution_choices,
                           mock_get_department_choices, mock_get_country_choices):

        mock_get_institution_choices.return_value = ((1, 'The University of Texas at Austin'),)
        mock_get_department_choices.return_value = ((127, 'Texas Advanced Computing Center'),)
        mock_get_country_choices.return_value = ((230, 'United States'),)

        response = self.client.get(reverse('tas:register'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<button type="submit" class="btn btn-success">Register Account</button>')

    @mock.patch('pytas.http.TASClient.save_user')
    @mock.patch('tas.views._create_ticket_for_pi_request')
    @mock.patch('tas.forms.get_country_choices')
    @mock.patch('tas.forms.get_department_choices')
    @mock.patch('tas.forms.get_institution_choices')
    def test_register_view_submit_not_pi(self, mock_get_institution_choices,
                                  mock_get_department_choices, mock_get_country_choices,
                                  mock_create_ticket_for_pi_request, mock_tas_save_user):

        mock_get_institution_choices.return_value = ((1, 'The University of Texas at Austin'),)
        mock_get_department_choices.return_value = ((127, 'Texas Advanced Computing Center'),)
        mock_get_country_choices.return_value = ((230, 'United States'),)

        form_data = mock_registration_form_data()

        self.client.post(reverse('tas:register'), form_data)
        self.assertFalse(mock_create_ticket_for_pi_request.called)
        self.assertTrue(mock_tas_save_user.called)

    @mock.patch('pytas.http.TASClient.save_user')
    @mock.patch('tas.views._create_ticket_for_pi_request')
    @mock.patch('tas.forms.get_country_choices')
    @mock.patch('tas.forms.get_department_choices')
    @mock.patch('tas.forms.get_institution_choices')
    def test_register_view_submit_pi(self, mock_get_institution_choices,
                                  mock_get_department_choices, mock_get_country_choices,
                                  mock_create_ticket_for_pi_request, mock_tas_save_user):

        mock_get_institution_choices.return_value = ((1, 'The University of Texas at Austin'),)
        mock_get_department_choices.return_value = ((127, 'Texas Advanced Computing Center'),)
        mock_get_country_choices.return_value = ((230, 'United States'),)

        form_data = mock_registration_form_data()
        form_data['request_pi_eligibility'] = 'on'

        self.client.post(reverse('tas:register'), form_data)
        self.assertTrue(mock_create_ticket_for_pi_request.called)
        self.assertTrue(mock_tas_save_user.called)


class EditProfileViewTests(TestCase):

    def setUp(self):
        fixture = test_user_fixture()
        self.test_user = get_user_model().objects.create_user(
                fixture['username'],
                fixture['email'],
                'password'
                )
        self.test_user.backend = 'tas.auth.TASBackend'

    @mock.patch('tas.forms.get_country_choices')
    @mock.patch('tas.forms.get_department_choices')
    @mock.patch('tas.forms.get_institution_choices')
    @mock.patch('pytas.http.TASClient.get_user')
    @mock.patch('django.contrib.auth.authenticate')
    @mock.patch('termsandconditions.models.TermsAndConditions.agreed_to_latest')
    def test_edit_profile_view(
        self, mock_terms_agreed_to_latest, mock_tas_authenticate, mock_tas_get_user,
        mock_get_institution_choices, mock_get_department_choices, mock_get_country_choices
    ):
        """
        Logged in users can access the edit profile view.
        """

        mock_terms_agreed_to_latest.return_value = True
        mock_tas_authenticate.return_value = self.test_user
        mock_tas_get_user.return_value = test_user_fixture()
        mock_get_institution_choices.return_value = ((1, 'The University of Texas at Austin'),)
        mock_get_department_choices.return_value = ((127, 'Texas Advanced Computing Center'),)
        mock_get_country_choices.return_value = ((230, 'United States'),)

        self.client.login(username='jdoe1', password='password')
        response = self.client.get(reverse('tas:profile_edit'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<h2>Edit Profile <small>| jdoe1 </small></h2>')

    @mock.patch('pytas.http.TASClient.get_user')
    @mock.patch('django.contrib.auth.authenticate')
    @mock.patch('termsandconditions.models.TermsAndConditions.agreed_to_latest')
    def test_edit_profile_view_source_not_chameleon(
        self, mock_terms_agreed_to_latest, mock_tas_authenticate, mock_tas_get_user
    ):
        """
        User accounts sourced from places other than Chameleon cannot edit their profile
        on the Chameleon Portal.
        """

        mock_terms_agreed_to_latest.return_value = True
        mock_tas_authenticate.return_value = self.test_user
        fixture = test_user_fixture()
        fixture['source'] = 'Standard'
        mock_tas_get_user.return_value = fixture

        self.client.login(username='jdoe1', password='password')
        response = self.client.get(reverse('tas:profile_edit'))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'http://testserver/user/profile/')

    @mock.patch('pytas.http.TASClient.save_user')
    @mock.patch('tas.views._create_ticket_for_pi_request')
    @mock.patch('tas.forms.get_country_choices')
    @mock.patch('tas.forms.get_department_choices')
    @mock.patch('tas.forms.get_institution_choices')
    @mock.patch('pytas.http.TASClient.get_user')
    @mock.patch('django.contrib.auth.authenticate')
    @mock.patch('termsandconditions.models.TermsAndConditions.agreed_to_latest')
    def test_edit_profile_submit(
        self, mock_terms_agreed_to_latest, mock_tas_authenticate, mock_tas_get_user,
        mock_get_institution_choices, mock_get_department_choices,
        mock_get_country_choices, mock_tas_save_user, mock_create_ticket_for_pi_request
    ):
        """
        POSTing the form on the edit profile page should call TASClient.save_user.
        """

        mock_terms_agreed_to_latest.return_value = True
        mock_tas_authenticate.return_value = self.test_user
        mock_tas_get_user.return_value = test_user_fixture()
        mock_get_institution_choices.return_value = ((1, 'The University of Texas at Austin'),)
        mock_get_department_choices.return_value = ((127, 'Texas Advanced Computing Center'),)
        mock_get_country_choices.return_value = ((230, 'United States'),)

        self.client.login(username='jdoe1', password='password')
        response = self.client.post(reverse('tas:profile_edit'), mock_registration_form_data())

        self.assertFalse(mock_create_ticket_for_pi_request.called)
        self.assertTrue(mock_tas_save_user.called)


    @mock.patch('pytas.http.TASClient.save_user')
    @mock.patch('tas.views._create_ticket_for_pi_request')
    @mock.patch('tas.forms.get_country_choices')
    @mock.patch('tas.forms.get_department_choices')
    @mock.patch('tas.forms.get_institution_choices')
    @mock.patch('pytas.http.TASClient.get_user')
    @mock.patch('django.contrib.auth.authenticate')
    @mock.patch('termsandconditions.models.TermsAndConditions.agreed_to_latest')
    def test_edit_profile_submit(
        self, mock_terms_agreed_to_latest, mock_tas_authenticate, mock_tas_get_user,
        mock_get_institution_choices, mock_get_department_choices,
        mock_get_country_choices, mock_tas_save_user, mock_create_ticket_for_pi_request
    ):
        """
        POSTing the form on the edit profile page should call TASClient.save_user. Also,
        when requesting PI Eligibility, a ticket should be created.
        """

        mock_terms_agreed_to_latest.return_value = True
        mock_tas_authenticate.return_value = self.test_user
        mock_tas_get_user.return_value = test_user_fixture()
        mock_get_institution_choices.return_value = ((1, 'The University of Texas at Austin'),)
        mock_get_department_choices.return_value = ((127, 'Texas Advanced Computing Center'),)
        mock_get_country_choices.return_value = ((230, 'United States'),)

        self.client.login(username='jdoe1', password='password')
        form_data = mock_registration_form_data()
        form_data['request_pi_eligibility'] = 'on'
        response = self.client.post(reverse('tas:profile_edit'), form_data)

        self.assertTrue(mock_create_ticket_for_pi_request.called)
        self.assertTrue(mock_tas_save_user.called)


class PasswordPolicy(TestCase):

    def setUp(self):
        self.test_user = {'username': 'jdoe1', 'firstName': 'John', 'lastName': 'Doe'}

    def test_password_match(self):
        valid, error = check_password_policy(self.test_user, 'aS1;', 'as1;')
        self.assertFalse(valid)
        self.assertTrue('does not match' in error)

    def test_password_length(self):
        valid, error = check_password_policy(self.test_user, 'aS1;', 'aS1;')
        self.assertFalse(valid)
        self.assertTrue('password provided is too short' in error)

    def test_password_character_class(self):
        valid, error = check_password_policy(self.test_user, 'asdf;qwerty', 'asdf;qwerty')
        self.assertFalse(valid)
        self.assertTrue('complexity requirements' in error)

    def test_password_username_token(self):
        valid, error = \
            check_password_policy(self.test_user, 'asdf;JDOE1;qwer', 'asdf;JDOE1;qwer')
        self.assertFalse(valid)
        self.assertTrue('name or username' in error)

    @mock.patch('pytas.http.TASClient.get_user')
    def test_password_full_name_token(self, mock_tas_get_user):
        mock_tas_get_user.return_value = test_user_fixture()
        valid, error = \
            check_password_policy(self.test_user, 'asdf;DOE1;qwer', 'asdf;DOE1;qwer')

        self.assertFalse(valid)
        self.assertTrue('name or username' in error)

    @mock.patch('pytas.http.TASClient.get_user')
    def test_password_valid(self, mock_tas_get_user):
        mock_tas_get_user.return_value = test_user_fixture()
        valid, error = \
            check_password_policy(self.test_user, 'a%4;D$$1!2qo(', 'a%4;D$$1!2qo(')

        self.assertTrue(valid)
        self.assertTrue(error is None)

class UserRegistrationFormTests(TestCase):

    @mock.patch('tas.forms.get_country_choices')
    @mock.patch('tas.forms.get_department_choices')
    @mock.patch('tas.forms.get_institution_choices')
    @mock.patch('tas.forms.check_password_policy')
    def test_user_registration_form_with_bad_username(self,
                                    mock_check_password_policy,
                                    mock_get_institution_choices,
                                    mock_get_department_choices,
                                    mock_get_country_choices):

        mock_get_institution_choices.return_value = ((1, 'The University of Texas at Austin'),)
        mock_get_department_choices.return_value = ((127, 'Texas Advanced Computing Center'),)
        mock_get_country_choices.return_value = ((230, 'United States'),)

        # an invalid username will not call the check_password_policy
        form_data = mock_registration_form_data()
        form_data['username'] = 'johndoe123'
        form = UserRegistrationForm(form_data)
        self.assertFalse(form.is_valid())
        self.assertTrue(form['username'].errors[0] == 'Enter a valid value.')
        self.assertFalse(mock_check_password_policy.called)


    @mock.patch('tas.forms.get_country_choices')
    @mock.patch('tas.forms.get_department_choices')
    @mock.patch('tas.forms.get_institution_choices')
    @mock.patch('pytas.http.TASClient.get_user')
    def test_user_registration_form(self,
                                    mock_tas_get_user,
                                    mock_get_institution_choices,
                                    mock_get_department_choices,
                                    mock_get_country_choices):

        mock_tas_get_user.return_value = test_user_fixture()
        mock_get_institution_choices.return_value = ((1, 'The University of Texas at Austin'),)
        mock_get_department_choices.return_value = ((127, 'Texas Advanced Computing Center'),)
        mock_get_country_choices.return_value = ((230, 'United States'),)

        form_data = mock_registration_form_data()
        form_data['password'] = form_data['confirmPassword'] = 'asdf;john;1234'
        form = UserRegistrationForm(form_data)
        self.assertTrue(form['password'].errors[0] == 'The password provided must not contain parts of your name or username.')
        self.assertFalse(form.is_valid())

        form_data = mock_registration_form_data()
        form = UserRegistrationForm(form_data)
        self.assertTrue(form.is_valid())

class PasswordResetConfirmFormTests(TestCase):

    @mock.patch('pytas.http.TASClient.get_user')
    def test_password_reset_form_username(self, mock_tas_get_user):
        mock_tas_get_user.side_effect = Exception('User not found', 'User not found with username bad_username')

        form_data = {
            'username': 'bad_username',
            'code': 'asdf1234asdf1234',
            'password': 'asdf;1234;',
            'confirm_password': 'asdf;1234;',
        }
        form = PasswordResetConfirmForm(form_data)
        self.assertFalse(form.is_valid())

    @mock.patch('pytas.http.TASClient.get_user')
    def test_password_reset_form_policy(self, mock_tas_get_user):
        mock_tas_get_user.return_value = test_user_fixture()

        form_data = {
            'username': 'jdoe1',
            'code': 'asdf1234asdf1234',
            'password': 'asdf;john;1235;',
            'confirm_password': 'asdf;john;1234;',
        }
        form = PasswordResetConfirmForm(form_data)
        self.assertFalse(form.is_valid())

        form_data = {
            'username': 'jdoe1',
            'code': 'asdf1234asdf1234',
            'password': 'asdf;john;1234;',
            'confirm_password': 'asdf;john;1234;',
        }
        form = PasswordResetConfirmForm(form_data)
        self.assertFalse(form.is_valid())

    @mock.patch('pytas.http.TASClient.confirm_password_reset')
    @mock.patch('pytas.http.TASClient.get_user')
    def test_password_reset_form_success(self, mock_tas_get_user,
                                         mock_tas_confirm_password_reset):

        mock_tas_get_user.return_value = test_user_fixture()
        mock_tas_confirm_password_reset.return_value = True

        form_data = {
            'username': 'jdoe1',
            'code': 'asdf1234asdf1234',
            'password': 'asdf;;1234;',
            'confirm_password': 'asdf;;1234;',
        }
        form = PasswordResetConfirmForm(form_data)
        self.assertTrue(form.is_valid())
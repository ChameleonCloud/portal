from django.test import TestCase
from tas.forms import *
import mock
import httpretty
import os

def mock_tas_get_user():
    user_json = """
    {
        "message": null,
        "status": "success",
        "result": {
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
            "email": "jdoe1@cs.utexas.edu",
            "departmentId": 127,
            "country": "United States",
            "department": "Department of Computer Science",
            "emailConfirmations": [],
            "institution": "University of Texas at Austin"
        }
    }
    """
    os.environ['TAS_URL'] = 'https://example.com/api'
    httpretty.register_uri(httpretty.GET,
                           'https://example.com/api/v1/users/username/jdoe1',
                           body=user_json, content_type='application/json')

# Create your tests here.
class PasswordPolicy(TestCase):

    def test_password_match(self):
        valid, error = check_password_policy('jdoe1', 'aS1;', 'as1;')
        self.assertFalse(valid)
        self.assertTrue('does not match' in error)

    def test_password_length(self):
        valid, error = check_password_policy('jdoe1', 'aS1;', 'aS1;')
        self.assertFalse(valid)
        self.assertTrue('password provided is too short' in error)

    def test_password_character_class(self):
        valid, error = check_password_policy('jdoe1', 'asdf;qwerty', 'asdf;qwerty')
        self.assertFalse(valid)
        self.assertTrue('complexity requirements' in error)

    def test_password_username_token(self):
        valid, error = check_password_policy('jdoe1', 'asdf;JDOE1;qwer', 'asdf;JDOE1;qwer')
        self.assertFalse(valid)
        self.assertTrue('name or username' in error)

    @httpretty.activate
    def test_password_full_name_token(self):
        mock_tas_get_user()
        valid, error = check_password_policy('jdoe1', 'asdf;DOE1;qwer', 'asdf;DOE1;qwer')

        self.assertFalse(valid)
        self.assertTrue('name or username' in error)

    @httpretty.activate
    def test_password_valid(self):
        mock_tas_get_user()
        valid, error = check_password_policy('jdoe1', 'a%4;D$$1!2qo(', 'a%4;D$$1!2qo(')

        self.assertTrue(valid)
        self.assertTrue(error is None)

    @httpretty.activate
    @mock.patch('tas.forms.check_password_policy')
    def test_user_account_form(self, mock_check_password_policy):
        mock_tas_get_user()

        # an invalid username will not call the check_password_policy
        form_data = {'username': 'johndoe123', 'password': 'asdf;1234', 'confirmPassword': 'asdf;1234'}
        form = UserAccountForm(form_data)
        self.assertFalse(form.is_valid())
        self.assertTrue(form['username'].errors[0] == 'Enter a valid value.')
        self.assertFalse(mock_check_password_policy.called)

        form_data = {'username': 'jdoe1', 'password': 'asdf;1234;john', 'confirmPassword': 'asdf;1234;john'}
        form = UserAccountForm(form_data)
        self.assertTrue(form['password'].errors[0] == 'The password provided must not contain parts of your name or username.')
        self.assertFalse(form.is_valid())

        form_data = {'username': 'jdoe1', 'password': 'asdf;1234', 'confirmPassword': 'asdf;1234'}
        form = UserAccountForm(form_data)
        self.assertTrue(form.is_valid())

    @mock.patch('tas.forms.check_password_policy')
    def test_user_account_form_with_bad_username(self, mock_check_password_policy):

        # an invalid username will not call the check_password_policy
        form_data = {'username': 'johndoe123', 'password': 'asdf;1234', 'confirmPassword': 'asdf;1234'}
        form = UserAccountForm(form_data)
        self.assertFalse(form.is_valid())
        self.assertTrue(form['username'].errors[0] == 'Enter a valid value.')
        self.assertFalse(mock_check_password_policy.called)

    @httpretty.activate
    def test_user_account_form(self):
        mock_tas_get_user()

        form_data = {'username': 'jdoe1', 'password': 'asdf;1234;john', 'confirmPassword': 'asdf;1234;john'}
        form = UserAccountForm(form_data)
        self.assertTrue(form['password'].errors[0] == 'The password provided must not contain parts of your name or username.')
        self.assertFalse(form.is_valid())

        form_data = {'username': 'jdoe1', 'password': 'asdf;1234', 'confirmPassword': 'asdf;1234'}
        form = UserAccountForm(form_data)
        self.assertTrue(form.is_valid())
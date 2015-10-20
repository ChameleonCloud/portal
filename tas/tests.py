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

def mock_registration_form_data():
    return {
        'firstName': 'John',
        'lastName': 'Doe',
        'email': 'jdoe1@cs.utexas.edu',
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
class PasswordPolicy(TestCase):

    def test_password_match(self):
        valid, error = check_password_policy({
                                                'username': 'jdoe1',
                                                'firstName': 'John',
                                                'lastName': 'Doe',
                                             },
                                             'aS1;',
                                             'as1;')
        self.assertFalse(valid)
        self.assertTrue('does not match' in error)

    def test_password_length(self):
        valid, error = check_password_policy({
                                                'username': 'jdoe1',
                                                'firstName': 'John',
                                                'lastName': 'Doe',
                                             },
                                             'aS1;',
                                             'aS1;')
        self.assertFalse(valid)
        self.assertTrue('password provided is too short' in error)

    def test_password_character_class(self):
        valid, error = check_password_policy({
                                                'username': 'jdoe1',
                                                'firstName': 'John',
                                                'lastName': 'Doe',
                                             },
                                             'asdf;qwerty',
                                             'asdf;qwerty')
        self.assertFalse(valid)
        self.assertTrue('complexity requirements' in error)

    def test_password_username_token(self):
        valid, error = check_password_policy({
                                                'username': 'jdoe1',
                                                'firstName': 'John',
                                                'lastName': 'Doe',
                                             },
                                             'asdf;JDOE1;qwer',
                                             'asdf;JDOE1;qwer')
        self.assertFalse(valid)
        self.assertTrue('name or username' in error)

    @httpretty.activate
    def test_password_full_name_token(self):
        mock_tas_get_user()
        valid, error = check_password_policy({
                                                'username': 'jdoe1',
                                                'firstName': 'John',
                                                'lastName': 'Doe',
                                             },
                                             'asdf;DOE1;qwer',
                                             'asdf;DOE1;qwer')

        self.assertFalse(valid)
        self.assertTrue('name or username' in error)

    @httpretty.activate
    def test_password_valid(self):
        mock_tas_get_user()
        valid, error = check_password_policy({
                                                'username': 'jdoe1',
                                                'firstName': 'John',
                                                'lastName': 'Doe',
                                             },
                                             'a%4;D$$1!2qo(',
                                             'a%4;D$$1!2qo(')

        self.assertTrue(valid)
        self.assertTrue(error is None)


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


    @httpretty.activate
    @mock.patch('tas.forms.get_country_choices')
    @mock.patch('tas.forms.get_department_choices')
    @mock.patch('tas.forms.get_institution_choices')
    def test_user_registration_form(self,
                                    mock_get_institution_choices,
                                    mock_get_department_choices,
                                    mock_get_country_choices):

        mock_tas_get_user()
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
from django.test import TestCase
from tas.forms import check_password_policy
import httpretty
import os

# Create your tests here.
class PasswordPolicy(TestCase):
    def test_password_match(self):
        valid, error = check_password_policy('jdoe1', 'aS1;', 'as1;')
        assert not valid
        assert 'does not match' in error

    def test_password_length(self):
        valid, error = check_password_policy('jdoe1', 'aS1;', 'aS1;')
        assert not valid
        assert 'password provided is too short' in error

    def test_password_character_class(self):
        valid, error = check_password_policy('jdoe1', 'asdf;qwerty', 'asdf;qwerty')
        assert not valid
        assert 'complexity requirements' in error

    def test_password_username_token(self):
        valid, error = check_password_policy('jdoe1', 'asdf;JDOE1;qwer', 'asdf;JDOE1;qwer')
        assert not valid
        assert 'name or username' in error

    @httpretty.activate
    def test_password_full_name_token(self):
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
        valid, error = check_password_policy('jdoe1', 'asdf;DOE1;qwer', 'asdf;DOE1;qwer')

        assert not valid
        assert 'name or username' in error
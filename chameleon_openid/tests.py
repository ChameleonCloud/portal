from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils.importlib import import_module
import mock

class SessionTestCase(TestCase):
    def setUp(self):
        engine = import_module(settings.SESSION_ENGINE)
        store = engine.SessionStore()
        store.save()
        self.session = store
        self.client.cookies[settings.SESSION_COOKIE_NAME] = store.session_key

class OpenIDViewsTests(SessionTestCase):

    @mock.patch('tas.forms.get_country_choices')
    @mock.patch('tas.forms.get_department_choices')
    @mock.patch('tas.forms.get_institution_choices')
    def test_openid_register_view(self, mock_get_institution_choices,
                           mock_get_department_choices, mock_get_country_choices):

        mock_get_institution_choices.return_value = ((1, 'The University of Texas at Austin'),)
        mock_get_department_choices.return_value = ((127, 'Texas Advanced Computing Center'),)
        mock_get_country_choices.return_value = ((230, 'United States'),)

        result = {}
        result['status'] = 'testing'
        result['url'] = 'http://example.com/openid.php?uri=testing'
        result['sreg'] = {
            'nickname': 'jdoe1',
            'email': 'jdoe1@example.com',
        }
        result['ax'] = {
            'projects': [],
            'full_name': 'John Doe',
        }

        self.session['openid'] = result
        self.session.save()

        response = self.client.get(reverse('chameleon_openid:openid_register'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, \
            'After registering you will be able to log in with either your GENI OpenID')
        self.assertContains(response, \
            '<input class="form-control" id="id_email" name="email" placeholder="Email"'
            ' required="required" title="" type="email" value="jdoe1@example.com" />')
from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils.importlib import import_module
import mock

class SessionTestCase(TestCase):
    def setUp(self):
        # http://code.djangoproject.com/ticket/10899
        settings.SESSION_ENGINE = 'django.contrib.sessions.backends.file'
        engine = import_module(settings.SESSION_ENGINE)
        store = engine.SessionStore()
        store.save()
        self.session = store
        self.client.cookies[settings.SESSION_COOKIE_NAME] = store.session_key

class OpenIDViewsTests(SessionTestCase):

    def test_openid_register_view(self):
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
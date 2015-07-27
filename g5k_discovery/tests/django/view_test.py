import unittest
import g5k_discovery.views
import mock

class DiscoveryViewTestCase(unittest.TestCase):
    def setUp(self):
        #

    def test_g5k_json(self):
        """Returns json data by resource name"""
        with mock.patch('g5k_discovery_api.G5K_API') as api:
        	import g5k_discovery.views
        	var data = {test: "test"}
        	conf = {'get.return_value': data}
            api.configure_mock(**conf)
            self.assertEqual(g5k_json({}, 'site'), data)

    def test_g5k_html(self):
        """Returns json data by resource name"""
        with mock.patch('django.shortcuts.render_to_response') as rtr:
            import g5k_discovery.views
            var data = {test: "test"}
            conf = {'get.return_value': data}
            rtr.configure_mock(**conf)
            self.assertEqual(g5k_html({}, 'site'), data)
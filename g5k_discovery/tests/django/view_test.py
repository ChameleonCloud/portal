# from django.test import SimpleTestCase
# import unittest
# import mock

# class DiscoveryViewTestCase(SimpleTestCase):
#     def setUp(self):
#         return None

#     def tearDown(self):
#         return None

#     def test_g5k_json(self):
#         """Returns json data by resource name"""
#         with mock.patch('g5k_discovery_api.G5K_API') as api:
#         	from g5k_discovery.views import g5k_json
#         	var data = {test: "test"}
#         	conf = {'call.return_value': data}
#             api.configure_mock(**conf)
#             self.assertEqual(g5k_json({}, 'site'), data)

#     def test_g5k_html(self):
#         """Returns html template by resource name"""
#         mock_render_to_response = mock.MagicMock()
#         with mock.patch.multiple('g5k_discovery.views',
#             render_to_response=mock_render_to_response,
#             RequestContext=mock.MagicMock(),
#             login_required=lambda x: x):
#             from g5k_discovery.views import g5k_html
#             mock_request = mock.Mock()
#             g5k_html(mock_request, 'site')
#             _, args, _ = mock_render_to_response.mock_calls[0]
#             self.assertEquals(args[0], 'g5k_discovery/site.html', 'Wrong template')
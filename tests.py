__author__ = 'claudio.melendrez'

from unittest import TestCase

try:
    from unittest import mock
except ImportError:
    import mock

from sonarqube_api import SonarAPIHandler
from sonarqube_api.exceptions import AuthError, ValidationError


class SonarAPIHandlerTest(TestCase):

    def setUp(self):
        self.h = SonarAPIHandler()

    @mock.patch('sonarqube_api.api.requests.Session.get')
    def test_validate_auth(self, mock_res):
        resp = mock.MagicMock(status_code=200)
        mock_res.return_value = resp

        # Error, not authenticated
        resp.json.return_value = {'valid': False}
        self.assertFalse(self.h.validate_authentication())

        # Weird result, always assume invalid
        resp.json.return_value = {'wtf': 'lala'}
        self.assertFalse(self.h.validate_authentication())

        # OK, authenticated
        resp.json.return_value = {'valid': True}
        self.assertTrue(self.h.validate_authentication())

    @mock.patch('sonarqube_api.api.requests.Session.get')
    def test_errors(self, mock_get):
        # Empty response , cannot get next
        resp = mock.MagicMock(status_code=200)
        resp.json.return_value = {'p': 1, 'ps': 20, 'total': 0, 'metrics': []}
        mock_get.return_value = resp
        self.assertRaises(StopIteration, next, self.h.get_metrics())

        # Not authenticated, raises AuthError
        resp.status_code = 401
        resp.reason = 'Unauthorized'
        self.assertRaises(AuthError, next, self.h.get_metrics())

        # Not authorized, raises AuthError
        resp.status_code = 403
        resp.reason = 'Forbidden'
        self.assertRaises(AuthError, next, self.h.get_metrics())

        # Invalid data, raises ValidationError
        resp.status_code = 400
        resp.json.return_value = {'errors': [{'msg': 'invalid data for field'}]}
        self.assertRaises(ValidationError, next, self.h.get_metrics())

    @mock.patch('sonarqube_api.api.requests.Session.post')
    def test_create_rule(self, mock_post):
        # Rule exists, error
        resp = mock.MagicMock(status_code=400)
        resp.json.return_value = {'errors': [{'msg': 'rule already exists'}]}
        mock_post.return_value = resp
        with self.assertRaises(ValidationError):
            self.h.create_rule('x1', 'Do not frobnicate', 'Frobnicating is wrong and should be avoided',
                               'Reemove forbnication', 'DEFFN/SJS', 'MAJOR', 'ACTIVE', 'XPath')

        # Simulate removal, now post is OK
        resp.status_code = 200
        resp.json.return_value = {'result': 'ok'}
        self.h.create_rule('x1', 'Do not frobnicate', 'Frobnicating is wrong and should be avoided',
                           'Reemove forbnication', 'DEFFN/SJS', 'major', 'active', 'XPath')

        # Check calls
        posted_data = {
            'custom_key': 'x1', 'name': 'Do not frobnicate',
            'markdown_description': 'Frobnicating is wrong and should be avoided',
            'params': 'message=Reemove forbnication;xpathQuery=DEFFN/SJS',
            'severity': 'MAJOR', 'status': 'ACTIVE', 'template_key': 'XPath'
        }
        mock_post.assert_called_with('http://localhost:9000/api/rules/create', data=posted_data)

    def test_get_metrics(self):
        self.skipTest('')

    def test_get_rules(self):
        self.skipTest('')

    def test_get_resources_debt(self):
        self.skipTest('')

    def test_get_resources_metrics(self):
        self.skipTest('')

    def test_get_resources_full_data(self):
        self.skipTest('')

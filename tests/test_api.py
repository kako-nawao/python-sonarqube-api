__author__ = 'claudio.melendrez'

from unittest import TestCase

try:
    from unittest import mock
except ImportError:
    import mock

from sonarqube_api import SonarAPIHandler
from sonarqube_api.exceptions import ClientError, AuthError, ValidationError, ServerError


class SonarAPIHandlerTest(TestCase):

    def setUp(self):
        self.h = SonarAPIHandler(user='admin', password='admin')

    def test_url_building(self):
        test = SonarAPIHandler(host='http://localhost', port=9001,
                               base_path='/testing')
        self.assertEqual(
            "http://localhost:9001/testing{}".format(test.RESOURCES_ENDPOINT),
            test._get_url(test.RESOURCES_ENDPOINT))

        test = SonarAPIHandler(host='http://localhost', port=9001)
        self.assertEqual(
            "http://localhost:9001{}".format(test.RESOURCES_ENDPOINT),
            test._get_url(test.RESOURCES_ENDPOINT))

        test = SonarAPIHandler(host='http://localhost')
        self.assertEqual(
            "http://localhost:9000{}".format(test.RESOURCES_ENDPOINT),
            test._get_url(test.RESOURCES_ENDPOINT))

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

        # Invalid data, raises ValidationError
        resp.status_code = 400
        resp.json.return_value = {'errors': [{'msg': 'invalid data for field'}]}
        self.assertRaises(ValidationError, next, self.h.get_metrics())

        # Not authenticated, raises AuthError
        resp.status_code = 401
        resp.reason = 'Unauthorized'
        self.assertRaises(AuthError, next, self.h.get_metrics())

        # Not authorized, raises AuthError
        resp.status_code = 403
        resp.reason = 'Forbidden'
        self.assertRaises(AuthError, next, self.h.get_metrics())

        # Not found, generic client error
        resp.status_code = 404
        resp.reason = 'Not Found'
        self.assertRaises(ClientError, next, self.h.get_metrics())

        # Server error
        resp.status_code = 500
        resp.reason = 'Internal Server Error'
        self.assertRaises(ServerError, next, self.h.get_metrics())

    @mock.patch('sonarqube_api.api.requests.Session.post')
    def test_activate_rule(self, mock_post):
        # Missing param key
        resp = mock.MagicMock(status_code=400)
        resp.json.return_value = {'errors': [{'msg': 'The rule_key parameter is missing'}]}
        mock_post.return_value = resp
        with self.assertRaises(ValidationError):
            self.h.activate_rule(None, 'py-234454', reset=True, severity='MAJOR', format='^setUp|tearDown$')

        # Check call, params and severity were ignored
        url = self.h._get_url(self.h.RULES_ACTIVATION_ENDPOINT)
        mock_post.assert_called_with(url, data={'rule_key': None, 'profile_key': 'py-234454', 'reset': 'true'})
        mock_post.reset_mock()

        # Now post proper data, with
        resp.status_code = 200
        resp.json.return_value = {'result': 'ok'}
        self.h.activate_rule('py:S1291', 'py-234454', format='^setUp|tearDown$')

        # Check call, params and severity added
        mock_post.assert_called_with(url, data={'rule_key': 'py:S1291', 'profile_key': 'py-234454',
                                                'reset': 'false', 'params': 'format=^setUp|tearDown$'})

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
        url = self.h._get_url(self.h.RULES_CREATE_ENDPOINT)
        mock_post.assert_called_with(url, data=posted_data)

    @mock.patch('sonarqube_api.api.SonarAPIHandler._make_call')
    def test_get_metrics(self, mock_call):
        # Two pages, once each
        resp = mock.MagicMock(status_code=200)
        resp.json.side_effect = [
            {'p': 1, 'ps': 2, 'total': 3, 'metrics': [{'project': 'lala', 'coverage': 70, 'violations': 56},
                                                      {'project': 'lele', 'coverage': 72, 'violations': 34}]},
            {'p': 2, 'ps': 2, 'total': 3, 'metrics': [{'project': 'lolo', 'coverage': 71, 'violations': 23}]},
        ]
        mock_call.return_value = resp

        # Get metrics with two fields (as list)
        resources = list(self.h.get_metrics(fields=['coverage', 'violations']))
        self.assertEqual(resources, [{'project': 'lala', 'coverage': 70, 'violations': 56},
                                     {'project': 'lele', 'coverage': 72, 'violations': 34},
                                     {'project': 'lolo', 'coverage': 71, 'violations': 23}])

        # Ensure make_call was called twice with correct params
        self.assertEqual(mock_call.call_count, 2)
        mock_call.assert_any_call(
            'get', self.h.METRICS_LIST_ENDPOINT, f='coverage,violations'
        )
        mock_call.assert_any_call(
            'get', self.h.METRICS_LIST_ENDPOINT, f='coverage,violations', p=2
        )

    @mock.patch('sonarqube_api.api.SonarAPIHandler._make_call')
    def test_get_rules(self, mock_call):
        # Two pages, once each
        resp = mock.MagicMock(status_code=200)
        resp.json.side_effect = [
            {'p': 1, 'ps': 2, 'total': 3, 'rules': [{'key': 'lala'}, {'key': 'lele'}]},
            {'p': 2, 'ps': 2, 'total': 3, 'rules': [{'key': 'lolo'}]},
        ]
        mock_call.return_value = resp

        # Get metrics with two fields (as list)
        resources = list(self.h.get_rules(profile='prof1', languages=['py', 'js']))
        self.assertEqual(resources, [{'key': 'lala'}, {'key': 'lele'}, {'key': 'lolo'}])

        # Ensure make_call was called twice with correct params
        self.assertEqual(mock_call.call_count, 2)
        mock_call.assert_any_call(
            'get', self.h.RULES_LIST_ENDPOINT, is_template='no', statuses='READY',
            activation='true', qprofile='prof1', languages='py,js'
        )
        mock_call.assert_any_call(
            'get', self.h.RULES_LIST_ENDPOINT, is_template='no', statuses='READY',
            activation='true', qprofile='prof1', languages='py,js', p=2
        )

    @mock.patch('sonarqube_api.api.SonarAPIHandler._make_call')
    def test_get_resources_metrics(self, mock_call):
        # Note: resource metrics responses are not paged
        resp = mock.MagicMock(status_code=200)
        resp.json.return_value = [
            {'name': 'lala', 'key': 'wow:lala', 'scope': 'PRJ',
             'msr': [{'key': 'coverage', 'val': 26.0, 'frmt_val': '26.0%'}]},
            {'name': 'lele', 'key': 'wow:lele', 'scope': 'PRJ',
             'msr': [{'key': 'coverage', 'val': 29.0, 'frmt_val': '29.0%'}]}
        ]
        mock_call.return_value = resp

        # Get metrics without specifying resource and no trends
        resources = list(self.h.get_resources_metrics())
        self.assertEqual(resources, [
            {'name': 'lala', 'key': 'wow:lala', 'scope': 'PRJ',
             'msr': [{'key': 'coverage', 'val': 26.0, 'frmt_val': '26.0%'}]},
            {'name': 'lele', 'key': 'wow:lele', 'scope': 'PRJ',
             'msr': [{'key': 'coverage', 'val': 29.0, 'frmt_val': '29.0%'}]}
        ])

        # Ensure make_call was called once with correct params
        mock_call.assert_called_once_with(
            'get', self.h.RESOURCES_ENDPOINT,
            metrics=','.join(self.h.GENERAL_METRICS)
        )
        mock_call.reset_mock()

        # Now get one resource, with metrics and trends
        resp.json.return_value = [
            {'name': 'lala', 'key': 'wow:lala', 'scope': 'PRJ',
             'msr': [{'key': 'coverage', 'val': 26.0, 'frmt_val': '26.0%'}]}
        ]
        resources = list(self.h.get_resources_metrics(
            resource='wow:lala', metrics=['coverage'], include_trends=True,
            include_modules=True
        ))
        self.assertEqual(resources, [
            {'name': 'lala', 'key': 'wow:lala', 'scope': 'PRJ',
             'msr': [{'key': 'coverage', 'val': 26.0, 'frmt_val': '26.0%'}]}
        ])

        # Check call
        mock_call.assert_called_once_with(
            'get', self.h.RESOURCES_ENDPOINT,
            resource='wow:lala', includetrends='true',
            metrics='coverage,new_coverage',
            qualifiers='TRK,BRC'
        )

    @mock.patch('sonarqube_api.api.SonarAPIHandler._make_call')
    def test_get_resources_debt(self, mock_call):
        # Note: resource metrics responses are not paged
        resp = mock.MagicMock(status_code=200)
        resp.json.return_value = [
            {'key': 'wow:wtf', 'name': 'Wizardly Table Fetching', 'scope': 'PRJ',
             'msr': [{'ctic_key': 'TESTABILITY', 'ctic_name': 'Testability',
                      'val': 121710.0, 'key': 'sqale_index', 'frmt_val': '253d'},
                     {'ctic_key': 'MAINTAINABILITY', 'ctic_name': 'Maintainability',
                      'val': 56916.0, 'key': 'sqale_index', 'frmt_val': '118d'}]}
        ]
        mock_call.return_value = resp

        # Get debts for testability
        resources = list(self.h.get_resources_debt(
            resource='wow:wtf', categories=['testability', 'maintainability'],
            include_trends=True, include_modules=True
        ))
        self.assertEqual(resources, [
            {'key': 'wow:wtf', 'name': 'Wizardly Table Fetching', 'scope': 'PRJ',
             'msr': [{'ctic_key': 'TESTABILITY', 'ctic_name': 'Testability',
                      'val': 121710.0, 'key': 'sqale_index', 'frmt_val': '253d'},
                     {'ctic_key': 'MAINTAINABILITY', 'ctic_name': 'Maintainability',
                      'val': 56916.0, 'key': 'sqale_index', 'frmt_val': '118d'}]}
        ])

        # Ensure make_call was called once with correct params
        mock_call.assert_called_once_with(
            'get', self.h.RESOURCES_ENDPOINT,
            resource='wow:wtf', model='SQALE', metrics='sqale_index',
            characteristics='TESTABILITY,MAINTAINABILITY', includetrends='true',
            qualifiers='TRK,BRC'
        )
        mock_call.reset_mock()

    @mock.patch('sonarqube_api.api.SonarAPIHandler._make_call')
    def test_get_resources_full_data(self, mock_call):
        # Setup responses for calls
        resp = mock.MagicMock(status_code=200)
        resp.json.side_effect = [
            # First call: get metrics
            [{'name': 'Wizardly Table Fetching', 'key': 'wow:wtf', 'scope': 'PRJ',
              'msr': [{'key': 'coverage', 'val': 26.0, 'frmt_val': '26.0%'}]}],
            # Second call: get debt (with wrong name) and a new project
            [{'key': 'wow:wtf', 'name': 'WTFdudeWrongName', 'scope': 'PRJ',
              'msr': [{'ctic_key': 'TESTABILITY', 'ctic_name': 'Testability',
                       'val': 121710.0, 'key': 'sqale_index', 'frmt_val': '253d'},
                      {'ctic_key': 'MAINTAINABILITY', 'ctic_name': 'Maintainability',
                       'val': 56916.0, 'key': 'sqale_index', 'frmt_val': '118d'}]},
             {'key': 'lol:hahaha', 'name': 'Another project', 'scope': 'PRJ',
              'msr': [{'ctic_key': 'TESTABILITY', 'ctic_name': 'Testability',
                       'val': 126.0, 'key': 'sqale_index', 'frmt_val': '2h 6m'},
                      {'ctic_key': 'MAINTAINABILITY', 'ctic_name': 'Maintainability',
                       'val': 12.0, 'key': 'sqale_index', 'frmt_val': '12m'}]}
             ]
        ]
        mock_call.return_value = resp

        # Make the call with one metric and two debt categories
        resources = list(self.h.get_resources_full_data(
            metrics=['coverage'],
            categories=['testability', 'maintainability'],
            include_modules=True
        ))

        # Ensure proper merge of data, first name use and sorting
        self.assertEqual(resources, [
            {'key': 'lol:hahaha', 'name': 'Another project', 'scope': 'PRJ',
             'msr': [{'ctic_key': 'TESTABILITY', 'ctic_name': 'Testability',
                      'val': 126.0, 'key': 'sqale_index', 'frmt_val': '2h 6m'},
                     {'ctic_key': 'MAINTAINABILITY', 'ctic_name': 'Maintainability',
                      'val': 12.0, 'key': 'sqale_index', 'frmt_val': '12m'}]},
            {'name': 'Wizardly Table Fetching', 'key': 'wow:wtf', 'scope': 'PRJ',
             'msr': [{'key': 'coverage', 'val': 26.0, 'frmt_val': '26.0%'},
                     {'ctic_key': 'TESTABILITY', 'ctic_name': 'Testability',
                      'val': 121710.0, 'key': 'sqale_index', 'frmt_val': '253d'},
                     {'ctic_key': 'MAINTAINABILITY', 'ctic_name': 'Maintainability',
                      'val': 56916.0, 'key': 'sqale_index', 'frmt_val': '118d'}]}
        ])

        # Ensure make_call was called twice with correct params
        # Note: do not use mock_calls or assert_has_calls or you'll get weird results, the list
        # contains ONLY a call that mas never made (p: 3) twice
        self.assertEqual(mock_call.call_count, 2)
        mock_call.assert_any_call(
            'get', self.h.RESOURCES_ENDPOINT,
            metrics='coverage', qualifiers='TRK,BRC'
        )
        mock_call.assert_any_call(
            'get', self.h.RESOURCES_ENDPOINT,
            model='SQALE', metrics='sqale_index',
            characteristics='TESTABILITY,MAINTAINABILITY',
            qualifiers='TRK,BRC'
        )

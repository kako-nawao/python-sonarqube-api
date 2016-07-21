__author__ = 'kako'

from io import StringIO
from unittest import TestCase

try:
    from unittest import mock
except ImportError:
    import mock

from sonarqube_api.api import SonarAPIHandler
from sonarqube_api.cmd import activate_rules, export_rules, migrate_rules


GET_RULES_DATA = [
    # Custom, use params
    {'langName': 'Python', 'key': 'L1456', 'name': 'Do not break userspace', 'debtRemFnOffset': 15,
     'severity': 'BLOCKER', 'htmlDesc': '<p>LOL, WTF bro</p>', 'mdDesc': 'LOL, WTF bro', 'status': 'ACTIVE',
     'params': [{'key': 'xpathQuery', 'defaultValue': 'lala'}, {'key': 'message', 'defaultValue': 'Broken'}],
     'templateKey': 'xpath'},
    # Another custom
    {'langName': 'Python', 'key': 'X123', 'name': 'Do not use so many elifs', 'debtRemFnOffset': 15,
     'severity': 'MAJOR', 'htmlDesc': '<p>LOL, WTF bro</p>', 'mdDesc': 'LOL, WTF bro', 'status': 'ACTIVE',
     'params': [{'key': 'xpathQuery', 'defaultValue': 'elifX5'}, {'key': 'message', 'defaultValue': 'Easy on the elifs'}],
     'templateKey': 'xpath'},
    # Not custom, no params
    {'langName': 'JavaScript', 'key': 'S1456', 'name': 'Missing semi-colon', 'debtRemFnCoeff': 5,
     'severity': 'MINOR', 'htmlDesc': '<p>yeah, your forgot about the semi-colon, dude</p>', 'mdDesc': 'haha',
     'params': [], 'status': 'ACTIVE', 'templateKey': 'xpath'},
    # Error, missing key data
    {'langName': 'Python', 'name': 'This rule is broken', 'debtRemFnCoeff': 12,
     'severity': 'MAJOR', 'htmlDesc': '<p>broken rule</p>', 'mdDesc': 'broken rule',
     'params': [], 'status': 'ACTIVE', 'templateKey': 'xpath'},
    # Custom again
    {'langName': 'JavaScript', 'key': 'X1456', 'name': 'wrong format', 'debtRemFnCoeff': 10,
     'severity': 'MINOR', 'htmlDesc': '<p>Oops</p>', 'mdDesc': 'Oops', 'status': 'ACTIVE',
     'params': [{'key': 'xpathQuery', 'defaultValue': 'lololo'}, {'key': 'message', 'defaultValue': 'Oops'}],
     'templateKey': 'xpath'},
]


class ExportRulesTest(TestCase):

    @mock.patch('sonarqube_api.cmd.export_rules.open', create=True)
    @mock.patch('sonarqube_api.cmd.export_rules.sys.stdout')
    @mock.patch('sonarqube_api.cmd.export_rules.sys.stderr')
    @mock.patch('csv.writer')
    @mock.patch('sonarqube_api.cmd.export_rules.argparse.ArgumentParser.parse_args')
    @mock.patch('sonarqube_api.api.SonarAPIHandler.get_rules')
    def test_main(self, get_rules_mock, parse_mock, writer_mock, stderr_mock,
                  stdout_mock, open_mock):
        # Set call arguments: active only, spec profile and langs
        parse_mock.return_value = mock.MagicMock(
            host='localhost', port='9000', user='pancho', password='primero',
            output='~', active=True, profile='prof1', languages='py,js'
        )

        # Mock file handlers
        html_file = mock.MagicMock()
        html_file.write.return_value = None
        csv_file = mock.MagicMock()
        open_mock.side_effect = [csv_file, html_file]

        # Set data to receive from server
        get_rules_mock.return_value = iter(GET_RULES_DATA)

        # Execute command
        export_rules.main()

        # Check call to get_rules, should be one
        get_rules_mock.assert_called_once_with(True, 'prof1', 'py,js')

        # Check error calls
        stderr_mock.write.assert_called_once_with("Error: missing values for key\n")

        # Check stdout write: 3 exported and 1 failed
        stdout_mock.write.assert_called_once_with('Complete rules export: 4 exported and 1 failed.\n')

        # Check calls to csv write, should have written header and three valid rules
        self.assertEqual(writer_mock.return_value.writerow.mock_calls, [
            mock.call(['language', 'key', 'name', 'debt', 'severity']),
            mock.call(['Python', 'L1456', 'Do not break userspace', 15, 'BLOCKER']),
            mock.call(['Python', 'X123', 'Do not use so many elifs', 15, 'MAJOR']),
            mock.call(['JavaScript', 'S1456', 'Missing semi-colon', 5, 'MINOR']),
            mock.call(['JavaScript', 'X1456', 'wrong format', 10, 'MINOR']),
        ])

        # TODO: add checks for html file write


class MigrateRulesTest(TestCase):

    @mock.patch('sonarqube_api.cmd.export_rules.sys.stdout')
    @mock.patch('sonarqube_api.cmd.export_rules.sys.stderr')
    @mock.patch('sonarqube_api.cmd.export_rules.argparse.ArgumentParser.parse_args')
    @mock.patch('sonarqube_api.api.SonarAPIHandler.get_rules')
    @mock.patch('sonarqube_api.api.requests.Session.post')
    def test_main(self, post_mock, get_rules_mock, parse_mock, stderr_mock, stdout_mock):
        # Set call arguments: active only, spec profile and langs
        parse_mock.return_value = mock.MagicMock(
            source_host='localhost', source_port='9000', source_user='pancho', source_password='primero',
            target_host='another.host', target_port='9000', target_user='pancho', target_password='primero',
        )

        # Set responses from source and target
        get_rules_mock.return_value = iter(GET_RULES_DATA)
        post_mock.side_effect = [
            # First rule: OK
            mock.MagicMock(status_code=200),
            # Second rule: repeated
            mock.MagicMock(status_code=400,
                           json=mock.MagicMock(return_value={'errors': [{'msg': 'Rule js:S1456 already exists.'}]})),
            # Third rule is ignored because it's not custom, no post
            # Fourth rule fails because it's missing key field, no post
            # Fifth rule: missing made-up field
            mock.MagicMock(status_code=400,
                           json=mock.MagicMock(return_value={'errors': [{'msg': 'Missing field newField.'}]})),
        ]

        # Execute command
        migrate_rules.main()

        # Check call to get_rules, should be one
        get_rules_mock.assert_called_once_with(active_only=True, custom_only=True)

        # Check error calls, should be one for last
        stderr_mock.write.assert_called_once_with("Failed to create rule X1456: Missing field newField.\n")

        # Check stdout write: 1 created, 1 skipped and 1 failed (1 w/o params ignored)
        stdout_mock.write.assert_called_once_with(
            "Complete rules migration: 1 created, 1 skipped (already existing) and 1 failed.\n"
        )


class ActivateRulesTest(TestCase):

    @mock.patch('sonarqube_api.cmd.activate_rules.open', create=True)
    @mock.patch('sonarqube_api.cmd.activate_rules.sys.stdout')
    @mock.patch('sonarqube_api.cmd.activate_rules.sys.stderr')
    @mock.patch('sonarqube_api.cmd.export_rules.argparse.ArgumentParser.parse_args')
    @mock.patch('sonarqube_api.api.requests.Session.post')
    def test_main(self, post_mock, parse_mock, stderr_mock,
                  stdout_mock, open_mock):
        # Set call arguments
        parse_mock.return_value = mock.MagicMock(
            host='localhost', port='9000', user='pancho', password='primero',
            profile_key='py-234345', filename='active-rules.csv', basepath=None
        )

        # Mock file handlers
        csv_file = StringIO(
            # Headers
            u'key,reset,severity,xpathQuery,message,format\n'
            # Standard rules: only reset first three
            'pylint:123,yes,,,,\n'
            'pylint:234,TRUE,,,,\n'
            'pylint:345,Y,,,,\n'
            'pylint:346,,,,,\n'
            # Customized rule: set severity and format
            'S123,,major,,,^foo|bar$\n'
            # Custom rule: set severity, xpath and message
            'X123,no,BLOCKER,\lala,Do not use lala,\n'
            # Error: incorrect severity
            'X123,no,so-so,\lala,Do not use lala,\n'
        )
        open_mock.return_value = csv_file

        # Set data to receive from server
        post_mock.side_effect = [
            # First fix rules OK
            mock.MagicMock(status_code=200),
            mock.MagicMock(status_code=200),
            mock.MagicMock(status_code=200),
            mock.MagicMock(status_code=200),
            mock.MagicMock(status_code=200),
            mock.MagicMock(status_code=200),
            # Sixth rule wrong: bad severity
            mock.MagicMock(status_code=400, json=mock.MagicMock(return_value={'errors': [{
                    'msg': "Value of parameter 'severity' (SO-SO) "
                           "must be one of: [INFO, MINOR, MAJOR, CRITICAL, BLOCKER]."
            }]})),
        ]

        # Execute command
        activate_rules.main()

        # Check post calls
        # Note: check by one to ease debugging
        h = SonarAPIHandler(host='localhost', port='9000', user='pancho', password='primero')
        url = h._get_url(h.RULES_ACTIVATION_ENDPOINT)
        self.assertEqual(post_mock.mock_calls[0], mock.call(
            url, data={'profile_key': 'py-234345', 'rule_key': 'pylint:123', 'reset': 'true'}
        ))
        self.assertEqual(post_mock.mock_calls[1], mock.call(
            url, data={'profile_key': 'py-234345', 'rule_key': 'pylint:234', 'reset': 'true'}
        ))
        self.assertEqual(post_mock.mock_calls[2], mock.call(
            url, data={'profile_key': 'py-234345', 'rule_key': 'pylint:345', 'reset': 'true'}
        ))
        self.assertEqual(post_mock.mock_calls[3], mock.call(
            url, data={'profile_key': 'py-234345', 'rule_key': 'pylint:346', 'reset': 'false'}
        ))
        self.assertEqual(post_mock.mock_calls[4], mock.call(
            url, data={'profile_key': 'py-234345', 'rule_key': 'S123', 'reset': 'false',
                       'severity': 'MAJOR', 'params': 'format=^foo|bar$'}
        ))
        self.assertEqual(post_mock.mock_calls[5], mock.call(
            url, data={'profile_key': 'py-234345', 'rule_key': 'X123', 'reset': 'false',
                       'severity': 'BLOCKER', 'params': 'message=Do not use lala;xpathQuery=\\lala'}
        ))
        self.assertEqual(post_mock.mock_calls[6], mock.call(
            url, data={'profile_key': 'py-234345', 'rule_key': 'X123', 'reset': 'false',
                       'severity': 'SO-SO', 'params': 'message=Do not use lala;xpathQuery=\\lala'}
        ))

        # Check error calls
        stderr_mock.write.assert_called_once_with(
            "Failed to activate rule X123: Value of parameter 'severity' "
            "(SO-SO) must be one of: [INFO, MINOR, MAJOR, CRITICAL, BLOCKER].\n"
        )

        # Check stdout write: 3 exported and 1 failed
        stdout_mock.write.assert_called_once_with('Complete rules activation: 6 activated and 1 failed.\n')

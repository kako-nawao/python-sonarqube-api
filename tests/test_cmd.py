__author__ = 'kako'

from unittest import TestCase

try:
    from unittest import mock
except ImportError:
    import mock

from sonarqube_api.cmd import export_rules
from sonarqube_api.cmd import migrate_rules
from sonarqube_api.exceptions import AuthError, ValidationError


class ExportRulesTest(TestCase):

    @mock.patch('sonarqube_api.cmd.export_rules.open')
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
        get_rules_mock.return_value = iter([
            # Custom, use params
            {'langName': 'Python', 'key': 'L1456', 'name': 'Do not break userspace', 'debtRemFnOffset': 15,
             'severity': 'BLOCKER', 'htmlDesc': '<p>LOL, WTF bro</p>',
             'params': [{'key': 'xpathQuery', 'defaultValue': 'lala'}, {'key': 'message', 'defaultValue': 'Broken'}]},
            # Not custom, no params
            {'langName': 'JavaScript', 'key': 'S1456', 'name': 'Missing semi-colon', 'debtRemFnCoeff': 5,
             'severity': 'MINOR', 'htmlDesc': '<p>yeah, your forgot about the semi-colon, dude</p>',
             'params': []},
            # Error, missing data
            {},
            # Last one is correct, but not written
            {'langName': 'JavaScript', 'key': 'X1456', 'name': 'wrong format', 'debtRemFnCoeff': 10,
             'severity': 'MINOR', 'htmlDesc': '<p>Oops</p>',
             'params': []},
        ])

        # Execute command
        export_rules.main()

        # Check call to get_rules, should be one
        get_rules_mock.assert_called_once_with(True, 'prof1', 'py,js')

        # Check error calls
        stderr_mock.write.assert_called_once_with("Error: missing values for langName\n")

        # Check stdout write: 3 exported and 1 failed
        stdout_mock.write.assert_called_once_with('Complete rules export: 3 exported and 1 failed.\n')

        # Check calls to csv write, should have written header and three valid rules
        self.assertEqual(writer_mock.return_value.writerow.mock_calls, [
            mock.call(['language', 'key', 'name', 'debt', 'severity']),
            mock.call(['Python', 'L1456', 'Do not break userspace', 15, 'BLOCKER']),
            mock.call(['JavaScript', 'S1456', 'Missing semi-colon', 5, 'MINOR']),
            mock.call(['JavaScript', 'X1456', 'wrong format', 10, 'MINOR']),
        ])

        # TODO: add checks for html file write


class MigrateRulesTest(TestCase):

    def test_main(self):
        self.skipTest('tomorrow')
        export_rules.main()


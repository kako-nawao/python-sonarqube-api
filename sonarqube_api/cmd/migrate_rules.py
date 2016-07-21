"""
Utility to migrate custom rules from one SonarQube server to another one.
"""
import argparse
import sys

from sonarqube_api.api import SonarAPIHandler, ValidationError


parser = argparse.ArgumentParser(description='Migrate custom rules from one '
                                             'SonarQube server to another')

# Source connection arguments
parser.add_argument('--source-host', dest='source_host', type=str,
                    default='http://localhost',
                    help='Host of the source SonarQube server')
parser.add_argument('--source-port', dest='source_port', type=str,
                    default='9000',
                    help='Port of the source SonarQube server instance')
parser.add_argument('--source-user', dest='source_user', type=str,
                    default=None,
                    help='Authentication user for source server')
parser.add_argument('--source-password', dest='source_password', type=str,
                    default=None,
                    help='Authentication password for source server')
parser.add_argument('--source-authtoken', dest='source_authtoken', type=str,
                    default=None,
                    help='Authentication token for source server')
parser.add_argument('--source-basepath', dest='source_basepath', type=str,
                    default=None,
                    help='The base-path of the source Sonar installation. Defaults to "/"')

# Target connection arguments
parser.add_argument('--target-host', dest='target_host', type=str,
                    default='http://localhost',
                    help='Host of the target SonarQube server')
parser.add_argument('--target-port', dest='target_port', type=str,
                    default='9000',
                    help='Port of the target SonarQube server instance')
parser.add_argument('--target-user', dest='target_user', type=str,
                    default=None,
                    help='Authentication user for target server')
parser.add_argument('--target-password', dest='target_password', type=str,
                    default=None,
                    help='Authentication password for target server')
parser.add_argument('--target-authtoken', dest='target_authtoken', type=str,
                    default=None,
                    help='Authentication token for target server')
parser.add_argument('--target-basepath', dest='target_basepath', type=str,
                    default=None,
                    help='The base-path of the target Sonar installation. Defaults to "/"')


def main():
    """
    Migrate custom rules from one server to another one using two
    SonarAPIHandler instances.
    """
    options = parser.parse_args()
    sh = SonarAPIHandler(host=options.source_host, port=options.source_port,
                         user=options.source_user, password=options.source_password,
                         token=options.source_authtoken, base_path=options.source_basepath)
    th = SonarAPIHandler(host=options.target_host, port=options.target_port,
                         user=options.target_user, password=options.target_password,
                         token=options.target_authtoken, base_path=options.target_basepath)

    # Get the generator of source rules
    rules = sh.get_rules(active_only=True, custom_only=True)

    # Counters (total, created, skipped and failed)
    c, s, f = 0, 0, 0

    # Now import and keep count
    try:
        for rule in rules:
            # Ensure we have params (only custom rules have them)
            params = rule.get('params')
            if params:
                # Ok, let's try to create it
                try:
                    # Get key, message, and xpath params
                    key = rule['key'].split(':')[-1]
                    message = None
                    xpath = None
                    for p in params:
                        if p['key'] == 'message':
                            message = p['defaultValue']
                        elif p['key'] == 'xpathQuery':
                            xpath = p['defaultValue']

                    # Now create it and increase counter
                    th.create_rule(key, rule['name'], rule['mdDesc'], message,
                                   xpath, rule['severity'], rule['status'],
                                   rule['templateKey'])
                    c += 1

                except ValidationError as e:
                    # Validation error, should continue execution afterwards
                    if 'already exists' in str(e):
                        # Rule already exists, skip
                        s += 1

                    else:
                        # Invalid data for rule creation, fail
                        f += 1
                        sys.stderr.write("Failed to create rule {}: "
                                         "{}\n".format(rule['key'], e))

    except Exception as e:
        # Other errors, stop execution immediately
        sys.stderr.write("Error: {}\n".format(e))
        status = 'Incomplete'

    else:
        # No errors, write result
        status = 'Complete'

    # Finally, write results
    sys.stdout.write("{} rules migration: {} created, {} skipped (already "
                     "existing) and {} failed.\n".format(status, c, s, f))

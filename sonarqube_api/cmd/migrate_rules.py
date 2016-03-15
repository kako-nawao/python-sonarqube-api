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


def run():
    """
    Migrate custom rules from one server to another one.
    """
    options = parser.parse_args()
    sh = SonarAPIHandler(options.source_host, options.source_port,
                         options.source_user, options.source_password)
    th = SonarAPIHandler(options.target_host, options.target_port,
                         options.target_user, options.target_password)

    # Get the generator of source rules
    rules = sh.get_rules(active_only=True, custom_only=True)

    # Keep counters for total, created, skipped and failed
    t, c, s, f = 0, 0, 0, 0

    # Now import and keep count
    try:
        for rule in rules:
            # Ensure we have params (only custom rules have them)
            params = rule.get('params')
            if params:
                # Ok, let's try to create it
                t += 1
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
                    # Ok, this could be an issue or not
                    if 'already exists' in str(e):
                        # Oh, it already existed there, no problem
                        s += 1

                    else:
                        # Oh, sometjing weent wrong, inform
                        f += 1
                        sys.stderr.write("Failed to create rule {}: "
                                         "{}\n".format(rule['key'], e))

    except Exception as e:
        sys.stderr.write("Error: {}\n".format(e))

    else:
        # Log final results
        sys.stdout.write("Done with creation of {} rules: {} created, {} skipped"
                         " (already existing) and {} failed.\n".format(t, c, s, f))


if __name__ == '__main__':
    run()

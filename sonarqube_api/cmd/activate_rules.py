"""
Utility to activate rules on a SonarQube server.
"""
import argparse
import csv
import sys

from sonarqube_api.api import SonarAPIHandler, ValidationError


parser = argparse.ArgumentParser(description='Activate rules in SonarQube server.')

# Rules arguments (required)
parser.add_argument('profile_key', type=str,
                    help='Key of the target profile to activate rules.')
parser.add_argument('filename', type=str,
                    help='File to use for source of the rules definitions.')

# Server connection params
parser.add_argument('--host', dest='host', type=str,
                    default='http://localhost',
                    help='Host of the source SonarQube server')
parser.add_argument('--port', dest='port', type=str,
                    default='9000',
                    help='Port of the source SonarQube server instance')
parser.add_argument('--user', dest='user', type=str,
                    default=None,
                    help='Authentication user for source server')
parser.add_argument('--password', dest='password', type=str,
                    default=None,
                    help='Authentication password for source server')
parser.add_argument('--authtoken', dest='authtoken', type=str,
                    default=None,
                    help='Authentication token for source server')
parser.add_argument('--basepath', dest='basepath', type=str,
                    default=None,
                    help='The base-path of the Sonar installation. Defaults to "/"')


def main():
    """
    Activate rules in a profile using a SonarAPIHandler instance.
    """
    options = parser.parse_args()
    h = SonarAPIHandler(host=options.host, port=options.port,
                        user=options.user, password=options.password,
                        token=options.authtoken, base_path=options.basepath)

    # Counters (total, created, skipped and failed)
    a, f = 0, 0

    # Read file and import
    try:
        with open(options.filename, 'r') as import_file:
            # Init reader and check headers
            reader = csv.DictReader(import_file)

            # Iterate rules and try to import them
            for rule_def in reader:
                key = rule_def.pop('key', None)
                try:
                    # Pop key, clean data and attempt activation
                    rule_def['reset'] = rule_def.get('reset', '').lower() in ('y', 'yes', 'true')
                    rule_def = {k: v for k, v in rule_def.items() if v}
                    h.activate_rule(key, options.profile_key, **rule_def)
                    a += 1

                except ValidationError as e:
                    # Invalid data, print error
                    sys.stderr.write("Failed to activate rule {}: "
                                     "{}\n".format(key, e))
                    f += 1

    except Exception as e:
        # Other errors, stop execution immediately
        sys.stderr.write("Error: {}\n".format(e))
        status = 'Incomplete'

    else:
        # No errors, write result
        status = 'Complete'

    # Finally, write results
    sys.stdout.write("{} rules activation: {} activated and "
                     "{} failed.\n".format(status, a, f))

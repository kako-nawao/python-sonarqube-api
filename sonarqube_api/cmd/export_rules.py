"""
Utility to export the rules on a SonarQube server.
"""
import argparse
import csv
import os
import sys

from sonarqube_api.api import SonarAPIHandler
from sonarqube_api.utils import utf_encode


parser = argparse.ArgumentParser(description='Export rules from a SonarQube server')

# Connection arguments
parser.add_argument('--host', dest='host', type=str,
                    default='http://localhost',
                    help='Host of the SonarQube server')
parser.add_argument('--port', dest='port', type=str,
                    default='9000',
                    help='Port of the SonarQube server instance')
parser.add_argument('--user', dest='user', type=str,
                    default=None,
                    help='Authentication user')
parser.add_argument('--password', dest='password', type=str,
                    default=None,
                    help='Authentication password')
parser.add_argument('--authtoken', dest='authtoken', type=str,
                    default=None,
                    help='Authentication token')
parser.add_argument('--basepath', dest='basepath', type=str,
                    default=None,
                    help='The base-path of the Sonar installation. Defaults to "/"')

# Output directory argument
parser.add_argument('--output-dir', dest='output', type=str,
                    default='~',
                    help='Output file')

# Rule filtering options
parser.add_argument('--active-only', dest='active', action='store_true',
                    help='Export only active rules')
parser.add_argument('--profile', dest='profile', type=str,
                    default='',
                    help='Export only rules for a given profile')
parser.add_argument('--languages', dest='languages', type=str,
                    default='',
                    help='Language to filter the rules to export')


# HTML rule section template
HTML_RULE_TEMPLATE = u'<h1 id="{}">{}</h1><dl><dt>Language</dt><dd>{}</dd>'\
                     u'<dt>Key</dt><dd>{}</dd><dt>Severity</dt><dd>{}</dd>'\
                     u'<dt>Debt</dt><dd>{}</dd><dt>Parameters</dt><dd>{}</dd>'\
                     u'</dl><div>{}</div><hr>'


def main():
    """
    Export a SonarQube's rules to a CSV and an HTML file, using a
    SonarAPIHandler connected to the given host.
    """
    options = parser.parse_args()
    h = SonarAPIHandler(host=options.host, port=options.port,
                        user=options.user, password=options.password,
                        token=options.authtoken, base_path=options.basepath)

    # Determine output csv and html file names
    csv_fn = os.path.expanduser(os.path.join(options.output, 'rules.csv'))
    html_fn = os.path.expanduser(os.path.join(options.output, 'rules.html'))

    # Open csv and html files
    with open(csv_fn, 'w') as csv_f, open(html_fn, 'w') as html_f:
        # Init csv writer and write header
        csv_w = csv.writer(csv_f)
        csv_w.writerow(['language', 'key', 'name', 'debt', 'severity'])

        # Start html file
        html_f.write(u'<html><body>')

        # Get the rules generator
        rules = h.get_rules(options.active,
                            options.profile,
                            options.languages)

        # Counters (total, exported and failed)
        s, f = 0, 0

        # Now import and keep count
        try:
            for rule in rules:
                try:
                    # Write CSV row
                    csv_w.writerow([
                        rule['langName'],
                        rule['key'],
                        rule['name'],
                        # Note: debt can be in diff. fields depending on type
                        rule.get('debtRemFnOffset',
                                 rule.get('debtRemFnCoeff', u'-')),
                        rule['severity']
                    ])

                    # Render parameters sublist
                    params_htmls = []
                    if rule['params']:
                        for param in rule['params']:
                            params_htmls.append(u'<li>{}: {}</li>'.format(
                                param.get('key', u'-'),
                                param.get('defaultValue', u'-')
                            ))
                    else:
                        params_htmls.append(u'-')

                    # Build values to write in html
                    values = (
                        rule['key'], rule['name'], rule['langName'],
                        rule['key'], rule['severity'],
                        rule.get('debtRemFnOffset', rule.get('debtRemFnCoeff', u'-')),
                        u''.join(params_htmls), rule.get('htmlDesc', u'-')
                    )

                    # Render html and write to file
                    html = utf_encode(HTML_RULE_TEMPLATE.format(*values))
                    html_f.write(html)
                    s += 1

                except KeyError as exc:
                    # Key error, should continue execution afterwards
                    sys.stderr.write("Error: missing values for {}\n".format(','.join(exc.args)))
                    f += 1

            # Done with rules, close html body and document
            html_f.write(u'</body></html>')

        except Exception as exc:
            # Other errors, stop execution immediately
            sys.stderr.write("Error: {}\n".format(exc))
            status = 'Incomplete'

        else:
            # No errors, complete
            status = 'Complete'

        # Finally, write results
        sys.stdout.write("{} rules export: {} exported and "
                         "{} failed.\n".format(status, s, f))

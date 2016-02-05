"""
Utility to export the rules on a SonarQube server.
"""
import argparse
import csv
import os

from api import SonarAPIHandler


# HTML rule section template
HTML_RULE_TEMPLATE = '<h1 id="{}">{}</h1><dl><dt>Language</dt><dd>{}</dd>' \
                     '<dt>Key</dt><dd>{}</dd><dt>Severity</dt><dd>{}</dd>' \
                     '<dt>Debt</dt><dd>{}</dd><dt>Parameters</dt><dd>{}</dd>' \
                     '</dl><div>{}</div><hr>'


parser = argparse.ArgumentParser(description='Export ')

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


def export_rules(options):
    """
    Export a SonarQube's rules to a CSV and an HTML file, using a
    SonarAPIHandler connected to the given host.
    """
    h = SonarAPIHandler(options.host, options.port, options.user, options.password)

    # Determine output csv and html file names
    csv_fn = os.path.expanduser(os.path.join(options.output, 'rules.csv'))
    html_fn = os.path.expanduser(os.path.join(options.output, 'rules.html'))

    # Open csv and html files
    with open(csv_fn, 'w') as csv_f, open(html_fn, 'w') as html_f:
        # Init csv writer and write header
        csv_w = csv.writer(csv_f)
        csv_w.writerow(['language', 'key', 'name', 'debt', 'severity'])

        # Start html file
        html_f.write('<html><body>')

        # Get the rules generator
        rules = h.get_rules(options.active,
                            options.profile,
                            options.languages)
        for rule in rules:
            # Write CSV row
            csv_w.writerow([
                rule['langName'],
                rule['key'],
                rule['name'],
                # Note: debt can be in diff. fields depending on type
                rule.get('debtRemFnOffset',
                         rule.get('debtRemFnCoeff', '-')),
                rule['severity']
            ])

            # Render parameters sublist
            params_htmls = []
            if rule['params']:
                for param in rule['params']:
                    params_htmls.append('<li>{}: {}</li>'.format(
                        param.get('key', '-'),
                        param.get('defaultValue', '-')
                    ))
            else:
                params_htmls.append('-')

            # Write html section
            html_f.write(
                HTML_RULE_TEMPLATE.format(
                    rule['key'], rule['name'], rule['langName'],
                    rule['key'], rule['severity'],
                    rule.get('debtRemFnOffset',
                             rule.get('debtRemFnCoeff', '-')),
                    ''.join(params_htmls),
                    rule.get('htmlDesc', '-')
                )
            )

        # Close html body and document
        html_f.write('</body></html>')


if __name__ == '__main__':
    # Executed (not imported), run export
    options = parser.parse_args()
    export_rules(options)

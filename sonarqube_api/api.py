"""
This module contains the SonarAPIHandler, used for communicating with the
SonarQube server web service API.
"""
import operator

import requests

from .exceptions import ClientError, AuthError, ValidationError, ServerError


class SonarAPIHandler(object):
    """
    Adapter for SonarQube's web service API.
    """
    # Default host is local
    DEFAULT_HOST = 'http://localhost'
    DEFAULT_PORT = 9000
    DEFAULT_BASE_PATH = ''

    # Endpoint for resources and rules
    AUTH_VALIDATION_ENDPOINT = '/api/authentication/validate'
    METRICS_LIST_ENDPOINT = '/api/metrics/search'
    RESOURCES_ENDPOINT = '/api/resources'
    RULES_ACTIVATION_ENDPOINT = '/api/qualityprofiles/activate_rule'
    RULES_LIST_ENDPOINT = '/api/rules/search'
    RULES_CREATE_ENDPOINT = '/api/rules/create'

    # Debt data params (characteristics and metric)
    DEBT_CHARACTERISTICS = (
        'TESTABILITY', 'RELIABILITY', 'CHANGEABILITY', 'EFFICIENCY',
        'USABILITY', 'SECURITY', 'MAINTAINABILITY', 'PORTABILITY', 'REUSABILITY'
    )
    DEBT_METRICS = (
        'sqale_index',
    )

    # General metrics with their titles (not provided by api)
    GENERAL_METRICS = (
        # SQUALE metrics
        'sqale_index', 'sqale_debt_ratio',

        # Violations
        'violations', 'blocker_violations', 'critical_violations',
        'major_violations', 'minor_violations',

        # Coverage
        'lines_to_cover', 'conditions_to_cover', 'uncovered_lines',
        'uncovered_conditions', 'coverage'
    )

    def __init__(self, host=None, port=None, user=None, password=None,
                 base_path=None, token=None):
        """
        Set connection info and session, including auth (if user+password
        and/or auth token were provided).
        """
        self._host = host or self.DEFAULT_HOST
        self._port = port or self.DEFAULT_PORT
        self._base_path = base_path or self.DEFAULT_BASE_PATH
        self._session = requests.Session()

        # Prefer revocable authentication token over username/password if
        # both are provided
        if token:
            self._session.auth = token, ''
        elif user and password:
            self._session.auth = user, password

    def _get_url(self, endpoint):
        """
        Return the complete url including host and port for a given endpoint.

        :param endpoint: service endpoint as str
        :return: complete url (including host and port) as str
        """
        return '{}:{}{}{}'.format(self._host, self._port, self._base_path, endpoint)

    def _make_call(self, method, endpoint, **data):
        """
        Make the call to the service with the given method, queryset and data,
        using the initial session.

        Note: data is not passed as a single dictionary for better testability
        (see https://github.com/kako-nawao/python-sonarqube-api/issues/15).

        :param method: http method (get, post, put, patch)
        :param endpoint: relative url to make the call
        :param data: queryset or body
        :return: response
        """
        # Get method and make the call
        call = getattr(self._session, method.lower())
        url = self._get_url(endpoint)
        res = call(url, data=data or {})

        # Analyse response status and return or raise exception
        # Note: redirects are followed automatically by requests
        if res.status_code < 300:
            # OK, return http response
            return res

        elif res.status_code == 400:
            # Validation error
            msg = ', '.join(e['msg'] for e in res.json()['errors'])
            raise ValidationError(msg)

        elif res.status_code in (401, 403):
            # Auth error
            raise AuthError(res.reason)

        elif res.status_code < 500:
            # Other 4xx, generic client error
            raise ClientError(res.reason)

        else:
            # 5xx is server error
            raise ServerError(res.reason)

    def activate_rule(self, key, profile_key, reset=False, severity=None,
                      **params):
        """
        Activate a rule for a given quality profile.

        :param key: key of the rule
        :param profile_key: key of the profile
        :param reset: reset severity and params to default
        :param severity: severity of rule for given profile
        :param params: customized parameters for the rule
        :return: request response
        """
        # Build main data to post
        data = {
            'rule_key': key,
            'profile_key': profile_key,
            'reset': reset and 'true' or 'false'
        }

        if not reset:
            # No reset, Add severity if given (if not default will be used?)
            if severity:
                data['severity'] = severity.upper()

            # Add params if we have any
            # Note: sort by key to allow checking easily
            params = ';'.join('{}={}'.format(k, v) for k, v in sorted(params.items()) if v)
            if params:
                data['params'] = params

        # Make call (might raise exception) and return
        res = self._make_call('post', self.RULES_ACTIVATION_ENDPOINT, **data)
        return res

    def create_rule(self, key, name, description, message, xpath, severity,
                    status, template_key):
        """
        Create a a custom rule.

        :param key: key of the rule to create
        :param name: name of the rule
        :param description: markdown description of the rule
        :param message: issue message (title) for the rule
        :param xpath: xpath query to select the violation code
        :param severity: default severity for the rule
        :param status: status of the rule
        :param template_key: key of the template from which rule is created
        :return: request response
        """
        # Build data to post
        data = {
            'custom_key': key,
            'name': name,
            'markdown_description': description,
            'params': 'message={};xpathQuery={}'.format(message, xpath),
            'severity': severity.upper(),
            'status': status.upper(),
            'template_key': template_key
        }

        # Make call (might raise exception) and return
        res = self._make_call('post', self.RULES_CREATE_ENDPOINT, **data)
        return res

    def get_metrics(self, fields=None):
        """
        Yield defined metrics.

        :param fields: iterable or comma-separated string of field names
        :return: generator that yields metric data dicts
        """
        # Build queryset including fields if required
        qs = {}
        if fields:
            if not isinstance(fields, str):
                fields = ','.join(fields)
            qs['f'] = fields.lower()

        # Page counters
        page_num = 1
        page_size = 1
        n_metrics = 2

        # Cycle through rules
        while page_num * page_size < n_metrics:
            # Update paging information for calculation
            res = self._make_call('get', self.METRICS_LIST_ENDPOINT,
                                  **qs).json()
            page_num = res['p']
            page_size = res['ps']
            n_metrics = res['total']

            # Update page number (next) in queryset
            qs['p'] = page_num + 1

            # Yield rules
            for metric in res['metrics']:
                yield metric

    def get_rules(self, active_only=False, profile=None, languages=None,
                  custom_only=False):
        """
        Yield rules in status ready, that are not template rules.

        :param active_only: filter only active rules
        :param profile: key of profile to filter rules
        :param languages: key of languages to filter rules
        :param custom_only: filter only custom rules
        :return: generator that yields rule data dicts
        """
        # Build the queryset
        qs = {'is_template': 'no', 'statuses': 'READY'}

        # Add profile and activity params
        if profile:
            qs.update({'activation': 'true', 'qprofile': profile})
        elif active_only:
            qs['activation'] = 'true'

        # Add language param
        # Note: we handle comma-separated string or list-like iterable)
        if languages:
            if not isinstance(languages, str):
                languages = ','.join(languages)
            qs['languages'] = languages.lower()

        # Filter by tech debt for custom only (custom have no tech debt)
        if custom_only:
            qs['has_debt_characteristic'] = 'false'

        # Page counters
        page_num = 1
        page_size = 1
        n_rules = 2

        # Cycle through rules
        while page_num * page_size < n_rules:
            # Update paging information for calculation
            res = self._make_call('get', self.RULES_LIST_ENDPOINT, **qs).json()
            page_num = res['p']
            page_size = res['ps']
            n_rules = res['total']

            # Update page number (next) in queryset
            qs['p'] = page_num + 1

            # Yield rules
            for rule in res['rules']:
                yield rule

    def get_resources_debt(self, resource=None, categories=None,
                           include_trends=False, include_modules=False):
        """
        Yield first-level resources with debt by category (aka. characteristic).

        :param resource: key of the resource to select
        :param categories: iterable of debt characteristics by name
        :param include_trends: include differential values for leak periods
        :param include_modules: include modules data
        :return: generator that yields resource debt data dicts
        """
        # Build parameters
        params = {
            'model': 'SQALE', 'metrics': ','.join(self.DEBT_METRICS),
            'characteristics': ','.join(categories or self.DEBT_CHARACTERISTICS).upper()
        }
        if resource:
            params['resource'] = resource
        if include_trends:
            params['includetrends'] = 'true'
        if include_modules:
            params['qualifiers'] = 'TRK,BRC'

        # Get the results
        res = self._make_call('get', self.RESOURCES_ENDPOINT, **params).json()

        # Yield results
        for prj in res:
            yield prj

    def get_resources_metrics(self, resource=None, metrics=None,
                              include_trends=False, include_modules=False):
        """
        Yield first-level resources with generic metrics.

        :param resource: key of the resource to select
        :param metrics: iterable of metrics to return by name
        :param include_trends: include differential values for leak periods
        :param include_modules: include modules data
        :return: generator that yields resource metrics data dicts
        """
        # Build parameters
        params = {}
        if not metrics:
            metrics = self.GENERAL_METRICS
        if resource:
            params['resource'] = resource
        if include_trends:
            params['includetrends'] = 'true'
            metrics.extend(['new_{}'.format(m) for m in metrics])
        if include_modules:
            params['qualifiers'] = 'TRK,BRC'
        params['metrics'] = ','.join(metrics)

        # Make the call
        res = self._make_call('get', self.RESOURCES_ENDPOINT, **params).json()

        # Iterate and yield results
        for prj in res:
            yield prj

    def get_resources_full_data(self, resource=None, metrics=None,
                                categories=None, include_trends=False,
                                include_modules=False):
        """
        Yield first-level resources with merged generic and debt metrics.

        :param resource: key of the resource to select
        :param metrics: iterable of metrics to return by name
        :param categories: iterable of debt characteristics by name
        :param include_trends: include differential values for leak periods
        :param include_modules: include modules data
        :return: generator that yields resource metrics and debt data dicts
        """
        # First make a dict with all resources
        prjs = {prj['key']: prj for prj in
                self.get_resources_metrics(
                    resource=resource, metrics=metrics,
                    include_trends=include_trends,
                    include_modules=include_modules
                )}

        # Now merge the debt data using the key
        for prj in self.get_resources_debt(
                resource=resource, categories=categories,
                include_trends=include_trends,
                include_modules=include_modules
        ):
            if prj['key'] in prjs:
                prjs[prj['key']]['msr'].extend(prj['msr'])
            else:
                prjs[prj['key']] = prj

        # Now yield all values
        for _, prj in sorted(prjs.items(), key=operator.itemgetter(0)):
            yield prj

    def validate_authentication(self):
        """
        Validate the authentication credentials passed on client initialization.
        This can be used to test the connection, since API always returns 200.

        :return: True if valid
        """
        res = self._make_call('get', self.AUTH_VALIDATION_ENDPOINT).json()
        return res.get('valid', False)

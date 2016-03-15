"""
This module contains the SonarAPIHandler, used for communicating with the
SonarQube server web service API.
"""
import requests

import copy
from .exceptions import AuthError, ValidationError


class SonarAPIHandler(object):
    """
    Adapter for SonarQube's web service API.
    """
    # Default host is local
    DEFAULT_HOST = 'http://localhost'
    DEFAULT_PORT = 9000

    # Endpoint for resources and rules
    AUTH_VALIDATION_ENDPOINT = '/api/authentication/validate'
    METRICS_LIST_ENDPOINT = '/api/metrics/search'
    RESOURCES_ENDPOINT = '/api/resources'
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

    # Differential metrics with their titles (not provided by api)
    NEW_METRICS = (
        # Violations
        'new_violations', 'new_blocker_violations', 'new_critical_violations',
        'new_major_violations', 'new_minor_violations',

        # Coverage
        'new_lines_to_cover', 'new_conditions_to_cover', 'new_uncovered_lines',
        'new_uncovered_conditions', 'new_coverage'

    )

    def __init__(self, host=None, port=None, user=None, password=None):
        """
        Set connection info and session, including auth (if user+password
        were provided).
        """
        self._host = host or self.DEFAULT_HOST
        self._port = port or self.DEFAULT_PORT
        self._session = requests.Session()
        if user and password:
            self._session.auth = user, password

    def _get_url(self, endpoint):
        """
        Return the complete url including host and port for a given endpoint.

        :param endpoint: service endpoint as str
        :return: complete url (including host and port) as str
        """
        return '{}:{}{}'.format(self._host, self._port, endpoint)

    def _make_call(self, method, endpoint, **data):
        """
        Make the call to the service with the given method, queryset and body,
        and whatever params were set initially (auth).

        Note: data is not passed as a single dictionary to ensure testability
        (see https://github.com/kako-nawao/python-sonarqube-api/issues/15).

        :param method: http method (get, post, put, patch) as str
        :param endpoint: relative url to make the call
        :param data: queryset or body
        :return: response
        """
        # Get method and make the call
        call = getattr(self._session, method.lower())
        url = self._get_url(endpoint)
        res = call(url, data=data or {})

        # Return res if res < 400, otherwise raise adequate exception
        if res.status_code < 400:
            return res

        elif res.status_code in (401, 403):
            raise AuthError(res.reason)

        elif res.status_code == 400:
            msg = ', '.join(e['msg'] for e in res.json()['errors'])
            raise ValidationError(msg)

    def create_rule(self, key, name, description, message, xpath, severity,
                    status, template_key):
        """
        Create a a custom rule in the connected server.

        :param rule_data: dictionary with rule data to create
        :return: True if rule was created, False if it already existed
        """
        data = {
            'custom_key': key,
            'name': name,
            'markdown_description': description,
            'params': 'message={};xpathQuery={}'.format(message, xpath),
            'severity': severity.upper(),
            'status': status.upper(),
            'template_key': template_key
        }
        res = self._make_call('post', self.RULES_CREATE_ENDPOINT, **data)
        return res

    def get_metrics(self, fields=None):
        """
        Get a generator with the specified metric data (or all if no key is given).
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
            res = self._make_call('get', self.METRICS_LIST_ENDPOINT, **qs).json()
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
        Get a generator of rules for the given active state, profile or
        languages (or all if none is given). Only READY, non-template rules
        are yielded.
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

    def get_resources_debt(self, resource=None, categories=None):
        """
        Get a generator of resources (or a single resource) data including
        the debt by category for the given categories (all by default).
        """
        # Build parameters
        params = {
            'model': 'SQALE', 'metrics': ','.join(self.DEBT_METRICS),
            'characteristics': ','.join(categories or self.DEBT_CHARACTERISTICS).upper()
        }
        if resource:
            params['resource'] = resource

        # Get the results
        res = self._make_call('get', self.RESOURCES_ENDPOINT, **params).json()

        # Yield results
        for prj in res:
            yield prj

    def get_resources_metrics(self, resource=None, metrics=None, include_trends=False):
        """
        Get a generator of resources (or a single resource) data including
        the given (or default) metrics.
        """
        # Build parameters
        params = {'metrics': ','.join(metrics or self.GENERAL_METRICS)}
        if resource:
            params['resource'] = resource
        if include_trends:
            params['includetrends'] = 'true'
            params['metrics'] = ','.join([params['metrics']] + list(self.NEW_METRICS))

        # Make the call
        res = self._make_call('get', self.RESOURCES_ENDPOINT, **params).json()

        # Iterate and yield results
        for prj in res:
            yield prj

    def get_resources_full_data(self, resource=None, metrics=None,
                                categories=None, include_trends=False):
        """
        Get a generator of resources (or a single resource) data including
        the given all merged metrics and debt data.
        """
        # First make a dict with all resources
        prjs = {prj['key']: prj for prj in
                self.get_resources_metrics(resource=resource, metrics=metrics,
                                           include_trends=include_trends)}

        # Now merge the debt data using the key
        for prj in self.get_resources_debt(resource=resource, categories=categories):
            prjs[prj['key']]['msr'].extend(prj['msr'])

        # Return only values (list-like object)
        for prj in prjs.values():
            yield prj

    def validate_authentication(self):
        """
        Validate the authentication credentials passed on client initialization.
        This can be used to test the connection, since the API always returns 200.

        :return: True if valid
        """
        res = self._make_call('get', self.AUTH_VALIDATION_ENDPOINT).json()
        return res.get('valid', False)

"""
This module contains the SonarAPIHandler, used for communicating with the
SonarQube server web service API.
"""

import requests
from requests.auth import HTTPBasicAuth


class SonarAPIHandler(object):
    """
    Adapter for SonarQube's web service API.
    """
    # Default host is local
    DEFAULT_HOST = 'http://localhost'
    DEFAULT_PORT = 9000

    # Endpoint for resources and rules
    METRICS_ENDPOINT = '/api/metrics/search'
    RESOURCES_ENDPOINT = '/api/resources'
    RULES_ENDPOINT = '/api/rules/search'
    TIMEMACHINE_ENDPOINT = '/api/timemachine'

    # Debt data params (characteristics and metric)
    DEBT_CHARACTERISTICS = (
        'TESTABILITY', 'RELIABILITY', 'CHANGEABILITY', 'EFFICIENCY',
        'USABILITY', 'SECURITY', 'MAINTAINABILITY', 'PORTABILITY', 'REUSABILITY'
    )
    DEBT_METRICS = (
        'sqale_index',
    )

    # General metrics with their titles (not provided by api)
    # Note: none of the new_* metrics are returned by the API
    GENERAL_METRICS = (
        # SQUALE metrics
        'sqale_index', 'sqale_debt_ratio',

        # Violations
        'violations', 'blocker_violations', 'critical_violations',
        'major_violations', 'minor_violations',
        'new_violations', 'new_blocker_violations', 'new_critical_violations',
        'new_major_violations', 'new_minor_violations',

        # Coverage metrics
        'lines_to_cover', 'conditions_to_cover', 'uncovered_lines',
        'uncovered_conditions', 'coverage'
        'new_lines_to_cover', 'new_conditions_to_cover', 'new_uncovered_lines',
        'new_uncovered_conditions', 'new_coverage'
    )

    @property
    def metrics_url(self):
        """
        URL to the metrics endpoint.
        """
        return '{}:{}{}'.format(self._host, self._port, self.METRICS_ENDPOINT)

    @property
    def resources_url(self):
        """
        URL to the resources endpoint.
        """
        return '{}:{}{}'.format(self._host, self._port, self.RESOURCES_ENDPOINT)

    @property
    def rules_url(self):
        """
        URL to the rules endpoint.
        """
        return '{}:{}{}'.format(self._host, self._port, self.RULES_ENDPOINT)

    def __init__(self, host=None, port=None, user=None, password=None):
        """
        Set connection and auth information (if user+password were provided).
        """
        self._host = host or self.DEFAULT_HOST
        self._port = port or self.DEFAULT_PORT
        self._call_params = {}
        if user and password:
            self._call_params['auth'] = HTTPBasicAuth(user, password)

    def _get_response(self, url, queryset=None):
        """
        Make the call to the service with the given queryset and whatever params
        were set initially (auth).
        """
        res = requests.get(url, data=queryset or {}, **self._call_params)
        if res.status_code != 200:
            raise Exception(res.reason)
        return res

    def get_metrics(self, key=None):
        """
        Get a generator with the specified (or all if no key is given)
        metric data.
        """
        # Queryset (for paging only)
        qs = {}

        # Page counters
        page_num = 1
        page_size = 1
        n_metrics = 2

        # Cycle through rules
        while page_num * page_size < n_metrics:
            # Update paging information for calculation
            res = self._get_response(self.metrics_url, qs).json()
            page_num = res['p']
            page_size = res['ps']
            n_metrics = res['total']

            # Update page number (next) in queryset
            qs['p'] = page_num + 1

            # Yield rules
            for metric in res['metrics']:
                yield metric

    def get_rules(self, active_only=False, profile=None, languages=None):
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

        # Page counters
        page_num = 1
        page_size = 1
        n_rules = 2

        # Cycle through rules
        while page_num * page_size < n_rules:
            # Update paging information for calculation
            res = self._get_response(self.rules_url, qs).json()
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
        res = self._get_response(self.resources_url, params).json()

        # Yield results
        for prj in res:
            yield prj

    def get_resources_metrics(self, resource=None, metrics=None):
        """
        Get a generator of resources (or a single resource) data including
        the given (or default) metrics.
        """
        # Build parameters
        params = {'metrics': ','.join(metrics or self.GENERAL_METRICS),
                  'includetrends': 'true'}
        if resource:
            params['resource'] = resource

        # Make the call
        res = self._get_response(self.resources_url, params).json()

        # Iterate and yield results
        for prj in res:
            yield prj

    def get_resources_full_data(self, resource=None, metrics=None):
        """
        Get a generator of resources (or a single resource) data including
        the given all merged metrics and debt data.
        """
        # First make a dict with all resources
        prjs = {prj['key']: prj for prj in self.get_resources_metrics(resource=resource, metrics=metrics)}

        # Now merge the debt data using the key
        for prj in self.get_resources_debt(resource=resource):
            prjs[prj['key']]['msr'].extend(prj['msr'])

        # Return only values (list-like object)
        for prj in prjs.values():
            yield prj

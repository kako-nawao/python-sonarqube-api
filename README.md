# Python SonarQube API

API Handler for SonarQube web service, providing basic authentication (which
seems to be the only kind that SonarQube supports) and a few methods to fetch
rules and metrics.


## Installation

Install from this repository:

    pip install -e git+git@github.com:kako-nawao/python-sonarqube-api.git#egg=sonarqube_api


## Usage

Example use:

    from sonarqube_api import SonarAPIHandler

    h = SonarAPIHandler(user='admin', password='admin')
    for metric in h.get_resources_full_data(metrics=['coverage', 'violations']):
        # do something with metrics...

Since the actual response data from SonarQube server is usually paged, all
methods return generators to optimize memory as well retrieval performance of
the first items.


## Supported Methods

The supported methods are:

* get_metrics: yield metrics definition
* get_rules: yield active rules
* get_resources_debt: yield projects with their technical debt by category
* get_resources_metrics: yield projects with some general metrics
* get_resources_full_data: yield projects with their general metrics and
technical debt by category (merge of previous two methods)


## Export Command

The package also provides a binary to export rules into csv and html files:

    export-sonarqube-rules


There are also many options you can pass to filter the rules:

    export-sonarqube-rules --user=admin --password=admin --active-only --languages=py,js


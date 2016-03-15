====================
Python SonarQube API
====================

API Handler for SonarQube web service, providing basic authentication (which
seems to be the only kind that SonarQube supports) and a few methods to fetch
metrics and rules, as well as methods to create rules and (soon) profiles.

Installation
============

Install from this repository::

    pip install sonarqube-api

Usage
=====

The API handler is easy to use, you just need to initialize it with the
connection parameters (by default *localhost* on port *9000* without
authentication) and use any of the methods to get the required information or
create rules.

Example getting projects with coverage and issues metrics::

    from sonarqube_api import SonarAPIHandler

    h = SonarAPIHandler(user='admin', password='admin')
    for project in h.get_resources_full_data(metrics=['coverage', 'violations']):
        # do something with project data...

Since the actual response data from SonarQube server is usually paged, all
methods return generators to optimize memory as well retrieval performance of
the first items.

You can also specify a single resources to fetch, but keep in mind that the resource methods
return generators, so you still need to *get the next object*::

    proj = next(h.get_resources_full_data(resource='some:example'))

Supported Methods
-----------------

The methods supported by the SonarAPIHandler are:

* ``create_rule``: create a rule in the server
* ``get_metrics``: yield metrics definition
* ``get_rules``: yield active rules
* ``get_resources_debt``: yield projects with their technical debt by category
* ``get_resources_metrics``: yield projects with some general metrics
* ``get_resources_full_data``: yield projects with their general metrics and technical debt by category (merge of previous two methods)

Commands
--------

The package also provides a few commands you can use from the shell to export
or migrate rules in SonarQube servers.

Export Rules
~~~~~~~~~~~~

The command ``export-sonarqube-rules`` reads the rules in a SonarQube server and
creates two files with their data. One is a *csv* with a snapshot of the rule
(including key, name, status, etc) and the other one is an *html* with all
the information, including description and examples.

The command uses sensible defaults, so the following::

    export-sonarqube-rules

Will export all rules on the server running at *localhost:9000* into the files
*rules.csv* and *rules.html* on your home directory.

But you can change the host, authentication, or filter the rules with a number
of available options::

    export-sonarqube-rules --host=http://sonar.example.com --user=admin --active-only --languages=py,js

For the complete set of export options run::

    export-sonarqube-rules -h

Migrate Rules
~~~~~~~~~~~~~

The command ``migrate-sonarqube-rules`` reads the custom rules in a SonarQube
server (the source) and tries to recreate them in another SonarQube server
(the target). Since by default it uses *localhost* for both source and target,
you'll need to specify at least one of the hosts.

For example, to copy all custom rules defined in server *sonar.from.com* to
server *sonar.to.com*, you would execute::

    migrate-sonarqube-rules --source-host=http://sonar.from.com --target-host=http://sonar.to.com

As with the previous command, you can specify all the connection options
(``--source-port``, ``--target-port``, ``--source-user``, etc).

For the complete set of export options run::

    migrate-sonarqube-rules -h

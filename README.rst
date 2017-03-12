====================
Python SonarQube API
====================

.. image:: https://img.shields.io/github/license/kako-nawao/python-sonarqube-api.svg
    :target: http://www.opensource.org/licenses/MIT

.. image:: https://img.shields.io/pypi/pyversions/sonarqube-api.svg
    :target: https://pypi.python.org/pypi/sonarqube-api
.. image:: https://img.shields.io/pypi/v/sonarqube-api.svg
    :target: https://pypi.python.org/pypi/sonarqube-api

.. image:: https://img.shields.io/travis/kako-nawao/python-sonarqube-api.svg
    :target: https://travis-ci.org/kako-nawao/python-sonarqube-api
.. image:: https://img.shields.io/codecov/c/github/kako-nawao/python-sonarqube-api.svg
    :target: https://codecov.io/gh/kako-nawao/python-sonarqube-api

API Handler for SonarQube web service, providing basic authentication (which
seems to be the only kind that SonarQube supports) and a few methods to fetch
metrics and rules, as well as methods to create rules and (soon) profiles.

Installation
============

Install from PyPI::

    pip install sonarqube-api

Compatibility
-------------

This package is compatible Python versions 2.7, 3.4, 3.5 and 3.6.
Probably others, but those are the ones against which we build (by Travis CI).


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

Sonar authentication tokens can also be used in place of username and password,
which is particularly useful when accessing the SonarQube API from a CI server,
as tokens can easily be revoked in the event of unintended exposure::

    h = SonarAPIHandler(token='f052f55b127bb06f63c31cb2064ea301048d9e5d')

Supported Methods
-----------------

The methods supported by the SonarAPIHandler are:

* ``activate_rule``: activate a rule for a given profile in the server
* ``create_rule``: create a rule in the server
* ``get_metrics``: yield metrics definition
* ``get_rules``: yield active rules
* ``get_resources_debt``: yield projects with their technical debt by category
* ``get_resources_metrics``: yield projects with some general metrics
* ``get_resources_full_data``: yield projects with their general metrics and technical debt by category (merge of previous two methods)
* ``validate_authentication``: validate authentication credentials

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

Activate Rules
~~~~~~~~~~~~~~

The command ``activate-sonarqube-rules`` reads an input csv file and activates
the rules on a SonarQube server for a quality profile, according to the
definitions on the file.

The command requires a profile key and a file name::

    activate-sonarqube-rules py-test-18349 active-rules.csv

As usual, you can customize all the server connection parameters, which you can
view with the help command::

    activate-sonarqube-rules -h

The file can be very simple: the only required field in the file is *key* (for
the rule key), but you can also define the *severity* and customize **any**
parameter such as *xpathQuery*, *message*, *format*... anything at all. You
can also use *reset* (which takes values *true*/*yes*) to force using defaults
for all values--for which rule all other params will be ignored.

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


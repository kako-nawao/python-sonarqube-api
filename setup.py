"""A setuptools based setup module.
See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""
# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path


here = path.abspath(path.dirname(__file__))

# Get the long description from the relevant file
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='sonarqube_api',

    # https://packaging.python.org/en/latest/single_source_version.html
    version='1.3.1',

    description='SonarQube API Handler',
    long_description=long_description,
    url='https://github.com/kako-nawao/python-sonarqube-api',
    author='Claudio Omar Melendrez Baeza',
    author_email='claudio.melendrez@gmail.com',
    license='MIT',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Plugins',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Software Development'
    ],

    keywords='api sonar sonarqube',
    packages=find_packages(exclude=['contrib', 'docs', 'test*']),

    # https://packaging.python.org/en/latest/requirements.html
    install_requires=[
        'requests>=2.9,<2.99',
    ],
    extras_require={},
    package_data={},

    # http://docs.python.org/3.4/distutils/setupscript.html#installing-additional-files # noqa
    data_files=[],

    # To provide executable scripts, use entry points in preference to the
    # "scripts" keyword. Entry points provide cross-platform support and allow
    # pip to create the appropriate form of executable for the target platform.
    entry_points={
        'console_scripts': [
            'activate-sonarqube-rules=sonarqube_api.cmd.activate_rules:main',
            'export-sonarqube-rules=sonarqube_api.cmd.export_rules:main',
            'migrate-sonarqube-rules=sonarqube_api.cmd.migrate_rules:main',
        ],
    },

    # Test suite (required for Py2)
    test_suite="tests",
)

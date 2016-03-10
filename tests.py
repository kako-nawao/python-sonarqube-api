__author__ = 'claudio.melendrez'

from unittest import TestCase

try:
    from unittest import mock
except ImportError:
    import mock


class DummyTest(TestCase):

    def test_env_works(self):
        self.assertEqual(1, 1)

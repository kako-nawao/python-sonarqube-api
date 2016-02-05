"""
This module contains a few pieces of funky code, used for testing
standard and custom XPATH rules.
"""


def mutable_params(x={}, y=[]):
    pass


def funcs_instead_of_literals(x, y, z):
    d_dumb_empty = dict()
    d_proper_empty = {}
    d_dumb = dict(a=x, b=y, c=z)
    d_proper = {'d': x, 'b': y, 'c': z}
    s_dumb = set([x, y, z])
    s_proper = {x, y, z}
    l_dumb_empty = list()
    l_proper_empty = []
    l_dumb = list((x, y, z))
    l_proper = [x, y, z]


def clumsy_membership_check(e, s):
    proper_check = e in s
    dumb_check = e in s.keys()



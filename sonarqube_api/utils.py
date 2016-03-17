__author__ = 'kako'

import sys


# Encoding cleanup function
if sys.version_info.major == 3:
    utf_encode = lambda x: x
else:
    utf_encode = lambda x: x.encode('utf-8')

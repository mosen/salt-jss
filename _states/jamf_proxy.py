# -*- coding: utf-8 -*-
'''
Manage JAMF Pro Instances.

Dependencies
============

- python-jss (testing branch currently).

'''
from __future__ import absolute_import, print_function, unicode_literals
import logging

logger = logging.getLogger(__name__)

# python-jss
HAS_LIBS = False
try:
    import jss
    from jss import jssobjects
    HAS_LIBS = True
except ImportError:
    pass

__virtualname__ = 'jamf'


def __virtual__():
    if not HAS_LIBS:
        return (
            False,
            'The following dependencies are required to use the jss modules: '
            'python-jss'
        )

    return __virtualname__




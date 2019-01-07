# -*- coding: utf-8 -*-
'''
Generate baseline proxy minion grains
'''
from __future__ import absolute_import
import salt.utils

__proxyenabled__ = ['jamf']

__virtualname__ = 'jamf'

def __virtual__():
    try:
        if salt.utils.platform.is_proxy() and __opts__['proxy']['proxytype'] == 'jamf':
            return __virtualname__
    except KeyError:
        pass

    return False


def main(proxy):
    return proxy['jamf.grains']()

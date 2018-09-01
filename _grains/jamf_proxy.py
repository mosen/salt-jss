# -*- coding: utf-8 -*-
'''
Generate baseline proxy minion grains
'''
from __future__ import absolute_import
import salt.utils.platform

__proxyenabled__ = ['jamf_proxy']

__virtualname__ = 'jamf_proxy'


def __virtual__():
    try:
        if salt.utils.platform.is_proxy() and __opts__['proxy']['proxytype'] == 'jamf_proxy':
            return __virtualname__
    except KeyError:
        pass

    return False

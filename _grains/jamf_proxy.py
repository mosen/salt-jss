# -*- coding: utf-8 -*-
'''
Generate baseline proxy minion grains
'''
from __future__ import absolute_import
import salt.utils
import logging

__proxyenabled__ = ['jamf']
__virtualname__ = 'jamf'

log = logging.getLogger(__file__)


def __virtual__():
    try:
        if salt.utils.platform.is_proxy() and __opts__['proxy']['proxytype'] == 'jamf':
            return __virtualname__
        else:
            log.debug('Platform is not proxy or proxy type is not jamf, not loading jamf grains.')
    except KeyError:
        log.warning('Could not read proxytype key from proxy pillar, check your pillar file for this proxy.')

    return False


def main(proxy):
    return proxy['jamf.grains']()

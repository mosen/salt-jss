# -*- coding: utf-8 -*-
'''
This proxy minion is able to communicate with a single JAMF instance.
'''
from __future__ import absolute_import, print_function, unicode_literals
import salt.utils.platform

# Import python libs
import logging

__proxyenabled__ = ['jamf_proxy']
__virtualname__ = 'jamf_proxy'

GRAINS_CACHE = {}
DETAILS = {}

log = logging.getLogger(__file__)


# python-jss
HAS_LIBS = False
try:
    import jss
    HAS_LIBS = True
    log.info('Loaded python-jss')
except ImportError:
    log.error('Failed to load required library `python-jss` for the jamf_proxy proxy module.')


def __virtual__():
    log.debug('jamf_proxy __virtual__() called...')
    if not HAS_LIBS:
        return (
            False,
            'The following dependencies are required to use the jss modules: '
            'python-jss'
        )

    if salt.utils.platform.is_proxy() and __opts__['proxy']['proxytype'] == 'jamf_proxy':
        return __virtualname__

    return False


def init(opts):
    log.debug('jamf_proxy proxy init() called...')
    DETAILS['initialized'] = True

    # Save the REST URL
    # DETAILS['url'] = opts['proxy']['url']


# def initialized():
#     '''
#     Since grains are loaded in many different places and some of those
#     places occur before the proxy can be initialized, return whether
#     our init() function has been called
#     '''
#     return DETAILS.get('initialized', False)
#
# def alive(opts):
#     '''
#     This function returns a flag with the connection state.
#     It is very useful when the proxy minion establishes the communication
#     via a channel that requires a more elaborated keep-alive mechanism, e.g.
#     NETCONF over SSH.
#     '''
#     log.debug('rest_sample proxy alive() called...')

def shutdown(opts):
    '''
    For this proxy shutdown is a no-op
    '''
    log.debug('rest_sample proxy shutdown() called...')

#
# def ping():
#     '''This function will check whether the JAMF Pro server API is available with the supplied creds.'''
#     return True


# def grains():
#     '''
#     Get the grains from the proxied device
#     '''
#     # if not DETAILS.get('grains_cache', {}):
#     #     DETAILS['grains_cache'] = {}
#     return {}
#
#
# def grains_refresh():
#     '''
#     Refresh the grains from the proxied device
#     '''
#     DETAILS['grains_cache'] = None
#     return grains()

# -*- coding: utf-8 -*-
'''
This proxy minion is able to communicate with a single JAMF instance.
'''
from __future__ import absolute_import, print_function, unicode_literals
import salt.utils.platform

# Import python libs
import logging
import salt.utils.http

__proxyenabled__ = ['jamf']
__virtualname__ = 'jamf'

GRAINS_CACHE = None
DETAILS = {}

log = logging.getLogger(__file__)


# python-jss
HAS_LIBS = False
try:
    import jss
    HAS_LIBS = True
    log.info('Loaded python-jss')
except ImportError:
    log.error('Failed to load required library `python-jss` for the jamf proxy module.')


def __virtual__():
    log.debug('jamf_proxy __virtual__() called...')
    if not HAS_LIBS:
        return (
            False,
            'The following dependencies are required to use the jss modules: '
            'python-jss'
        )

    if salt.utils.platform.is_proxy() and __opts__['proxy']['proxytype'] == 'jamf':
        return __virtualname__

    return False


def init(opts):
    log.debug('jamf_proxy proxy init() called...')
    DETAILS['url'] = opts['proxy']['url']
    DETAILS['jss'] = jss.JSS(
        url=opts['proxy']['url'],
        user=opts['proxy']['username'],
        password=opts['proxy']['password'],
        ssl_verify=opts['proxy'].get('ssl_verify', True),
    )
    DETAILS['initialized'] = True


def initialized():
    '''
    Since grains are loaded in many different places and some of those
    places occur before the proxy can be initialized, return whether
    our init() function has been called
    '''
    return DETAILS.get('initialized', False)


def shutdown(opts):
    '''
    For this proxy shutdown is a no-op
    '''
    log.debug('jamf proxy shutdown() called...')


def ping():
    '''
    Is the REST server up?
    '''
    r = salt.utils.http.query(DETAILS['url'], decode_type='json', decode=True)
    return True


def grains():
    '''
    Get the grains from the proxied device
    '''
    global GRAINS_CACHE

    if GRAINS_CACHE is None:
        GRAINS_CACHE = {}
        health = salt.utils.http.query("{}healthCheck.html".format(DETAILS['url']), decode_type='json', decode=True)
        setup_complete = (len(health) == 0)
        GRAINS_CACHE['jamf_setup_complete'] = setup_complete

        if not setup_complete:
            status = health[0]
            GRAINS_CACHE['jamf_setup_health_code'] = status['healthCode']
            GRAINS_CACHE['jamf_setup_description'] = status['description']
        else:
            system_info = DETAILS['jss'].uapi.SystemInformation()
            GRAINS_CACHE['jamf_is_byod_enabled'] = system_info['isByodEnabled']
            GRAINS_CACHE['jamf_is_cloud_deployments_enabled'] = system_info['isCloudDeploymentsEnabled']
            GRAINS_CACHE['jamf_is_dep_account_enabled'] = system_info['isDepAccountEnabled']
            GRAINS_CACHE['jamf_is_patch_enabled'] = system_info['isPatchEnabled']
            GRAINS_CACHE['jamf_is_sso_saml_enabled'] = system_info['isSsoSamlEnabled']
            GRAINS_CACHE['jamf_is_user_migration_enabled'] = system_info['isUserMigrationEnabled']
            GRAINS_CACHE['jamf_is_vpp_token_enabled'] = system_info['isVppTokenEnabled']
            GRAINS_CACHE['jamf_sso_saml_login_uri'] = system_info.get('ssoSamlLoginUri', None)  # This can be undefined

            lobby = DETAILS['jss'].uapi.Lobby()
            GRAINS_CACHE['jamf_version'] = lobby['version']

            startup_status = DETAILS['jss'].uapi.StartupStatus()
            GRAINS_CACHE['jamf_startup_percentage'] = startup_status['percentage']
            GRAINS_CACHE['jamf_startup_step'] = startup_status['step']

    return GRAINS_CACHE


def grains_refresh():
    '''
    Refresh the grains from the proxied device
    '''
    global GRAINS_CACHE

    log.debug('Refreshing jamf proxy grains')
    GRAINS_CACHE = None
    return grains()


def get_details():
    '''Return information about the configuration of this proxy minion.'''
    global DETAILS

    return DETAILS

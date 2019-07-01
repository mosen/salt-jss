# -*- coding: utf-8 -*-
'''
Manage a JAMF Pro instance via the JAMF API

This module contains all execution module functions that relate to UAPI based settings.

:maintainer:    Mosen <mosen@noreply.users.github.com>
:maturity:      beta
:depends:       python-jss
:platform:      darwin
'''
import logging
import os
import difflib
import plistlib
from xml.etree import ElementTree
from xml.sax.saxutils import unescape
import salt.utils.locales
import salt.utils.data
from salt.exceptions import (
    CommandExecutionError, MinionError, SaltInvocationError
)
import salt.utils.platform

logger = logging.getLogger(__name__)

__proxyenabled__ = ['jamf']
__virtualname__ = 'jamf'

# python-jss
HAS_LIBS = False
try:
    import jss
    from jss import uapiobjects
    HAS_LIBS = True
except ImportError:
    pass


def __virtual__():
    '''
    Only work on proxy
    '''
    if not HAS_LIBS:
        return (
            False,
            'The following dependencies are required to use the jss modules: '
            'python-jss'
        )

    if salt.utils.platform.is_proxy():
        return __virtualname__
    return (False, 'The jamf_proxy execution module failed to load: '
                   'only available on proxy minions.')


def _get_jss():
    proxy = __pillar__['proxy']
    logger.debug('Using JAMF Pro URL: {}'.format(proxy['url']))

    j = jss.JSS(
        url=proxy['url'],
        user=proxy['username'],
        password=proxy['password'],
        ssl_verify=proxy.get('ssl_verify'),
    )

    return j


def get_enrollment():
    '''
    Get the current enrollment settings.

    CLI Example:

    .. code-block:: bash

        salt '*' jamf_settings.get_enrollment
    '''
    j = _get_jss()
    settings = j.uapi.EnrollmentSetting()
    return dict(settings)


def set_enrollment(values):
    '''
    Set the current enrollment settings.

    '''
    j = _get_jss()
    settings = uapiobjects.EnrollmentSetting(j, values)
    try:
        logger.debug(dict(settings))
        settings.save()
    except jss.PutError as e:
        raise CommandExecutionError("Error saving object: {}".format(e.message))

    return True


def get_inventory_collection(as_object=False):
    '''
    Get the current inventory collection settings.

    as_object (bool)
        Internal use only, returns python-jss object.
    '''
    j = _get_jss()
    settings = j.ComputerInventoryCollection()
    if as_object:
        return settings
    else:
        return str(settings)


def get_self_service():
    '''
    Get the current self-service settings.

    CLI Example:

    .. code-block:: bash

        salt '*' jamf_settings.get_self_service
    '''
    j = _get_jss()
    settings = j.SelfServiceSettings()
    return dict(settings)

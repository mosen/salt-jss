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

# python-jss
HAS_LIBS = False
try:
    import jss
    HAS_LIBS = True
except ImportError:
    pass

__virtualname__ = 'jamf_settings'

logger = logging.getLogger(__name__)


def __virtual__():
    if not HAS_LIBS:
        return (
            False,
            'The following dependencies are required to use the jamf modules: '
            'python-jss'
        )

    if salt.utils.platform.is_proxy():
        return (
            False,
            'jamf_local modules are not designed to run on proxy minions.'
        )

    return __virtualname__

def _get_jss():
    jss_options = __salt__['config.option']('jss')
    # jss_url = __salt__['config.option']('jss.url')
    # jss_user = __salt__['config.option']('jss.username')
    # jss_password = __salt__['config.option']('jss.password')
    # jss_ssl_verify = __salt__['config.option']('jss.ssl_verify', True)

    logger.debug('Using JAMF Pro URL: {}'.format(jss_options['url']))

    j = jss.JSS(
        url=jss_options['url'],
        user=jss_options['username'],
        password=jss_options['password'],
        ssl_verify=jss_options['ssl_verify'],
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
    settings = jss.EnrollmentSetting(j, values)
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

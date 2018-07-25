# -*- coding: utf-8 -*-
'''
Manage a JAMF Pro instance via the JAMF API

This module contains all execution module functions that relate to extension attributes for computers, mobile devices
and users.

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

# python-jss
HAS_LIBS = False
try:
    import jss
    HAS_LIBS = True
except ImportError:
    pass

__virtualname__ = 'jamf_ea'

logger = logging.getLogger(__name__)


def __virtual__():
    if not HAS_LIBS:
        return (
            False,
            'The following dependencies are required to use the jamf modules: '
            'python-jss'
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


def get_computer_ea(name=None, id=None, format='dict'):
    '''
    Get a computer extension attribute by ID or Name

    name
        The computer extension attribute name. This cannot be supplied with id
    id
        The computer extension attribute ID. If this is supplied, name is ignored
    format
        The format to return the result in. Default is 'dict' which is kinder to serialisation, but 'obj' is reserved
        for use by other execution modules.

    CLI Example:

    .. code-block:: bash

        salt '*' jamf_ea.get_computer_ea id=1
        salt '*' jamf_ea.get_computer_ea name="something"

    '''

    if id is None and name is None:
        raise SaltInvocationError('You must provide either a name or id parameter')

    j = _get_jss()
    try:

        if id is not None:
            ea = j.ComputerExtensionAttribute(id)
        elif name is not None:
            ea = j.ComputerExtensionAttribute("name={}".format(name))
        else:
            ea = None
            return ea

        result = {
            'id': ea.findtext('id'),
            'name': ea.findtext('name'),
            'description': ea.findtext('description'),
            'data_type': ea.findtext('data_type'),
            'input_type': ea.findtext('input_type/type'),
            'inventory_display': ea.findtext('inventory_display'),
        }

        if result['input_type'] == 'script':
            result['script'] = ea.findtext('input_type/script')

        return result
    except jss.JSSGetError as e:
        raise CommandExecutionError(
            'Unable to retrieve computer extension attribute(s), {0}'.format(e.message)
        )

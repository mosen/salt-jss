# -*- coding: utf-8 -*-
'''
Manage a JAMF Pro instance via the JAMF API

:maintainer:    Mosen <mosen@noreply.users.github.com>
:maturity:      beta
:depends:       python-jss
:platform:      darwin
:configuration:
    - jss_url: URL to jss
    - jss_verify_ssl (bool): Verify SSL certificate
    -
'''
import logging
import os
import difflib
from xml.etree import ElementTree
import salt.utils.locales
import salt.utils.data
from salt.exceptions import (
    CommandExecutionError, MinionError, SaltInvocationError
)
# can't use get_hash because it only operates on files, not buffers/bytes
from salt.utils.hashutils import md5_digest, sha256_digest, sha512_digest

# python-jss
HAS_LIBS = False
try:
    import jss
    HAS_LIBS = True
except ImportError:
    pass

__virtualname__ = 'jamf'

logger = logging.getLogger(__name__)


def __virtual__():
    if not HAS_LIBS:
        return (
            False,
            'The following dependencies are required to use the jss modules: '
            'python-jss'
        )

    if salt.utils.platform.is_proxy():
        return (
            False,
            'This module is designed for local execution'
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


def activation_code():
    '''
    Retrieve the current activation details.

    CLI Example:

    .. code-block:: bash

        salt-call jamf.activation_code
    '''
    j = _get_jss()
    try:
        activation_code = j.ActivationCode()
    except jss.GetError as e:
        raise CommandExecutionError(
            'Unable to retrieve Activation Code, {0}'.format(e.message)
        )

    return {
        'organization_name': activation_code.findtext('organization_name'),
        'code': activation_code.findtext('code'),
    }


def computers(match=None):
    '''
    Retrieve all enrolled computers.

    match
        Text search which generally applies to many fields eg name, mac address, ip address...
        An asterisk '*' must be used as a wildcard, and you should quote it in CLI usage.

    .. code-block:: bash

        salt-call jamf.computers
        salt-call jamf.computers match='comp*'

    '''
    j = _get_jss()
    try:
        if match is not None:
            computers = j.Computer('match={}'.format(match))
        else:
            computers = j.Computer()

    except jss.GetError as e:
        raise CommandExecutionError(
            'Unable to retrieve Computers, {0}'.format(e.message)
        )

    def _generate_computer_result(c):
        if c.find('general') is None:
            return {
                'id': c.id,
                'name': c.name,
            }
        else:
            return {
                'id': c.id,
                'name': c.name,
                'mac_address': c.general.mac_address.text,
                'ip_address': c.general.ip_address.text,
                'serial_number': c.general.serial_number.text,
                'udid': c.general.udid.text,
            }

    if len(computers) > 0:
        result = [_generate_computer_result(c) for c in computers]
        return result
    else:
        return None


def ldap_servers():
    '''
    Retrieve a list of configured LDAP servers

    CLI Example:

    .. code-block:: bash

        salt-call jamf.list_ldap_servers
    '''
    j = _get_jss()
    try:
        ldap_servers = j.LDAPServer()
    except jss.GetError as e:
        raise CommandExecutionError(
            'Unable to retrieve LDAP server(s), {0}'.format(e.message)
        )

    return ldap_servers


def ldap_server(name=None, id=None):
    '''
    Retrieve a single LDAP server

    CLI Example:

    .. code-block:: bash

        salt-call jamf.ldap_server name="Name"
        salt-call jamf.ldap_server id=1
    '''
    if id is None and name is None:
        raise SaltInvocationError('You must provide either a name or id parameter')

    j = _get_jss()
    try:
        result = j.LDAPServer(name)
    except jss.JSSGetError as e:
        raise CommandExecutionError(
            'Unable to retrieve LDAP server(s), {0}'.format(e.message)
        )

    return result


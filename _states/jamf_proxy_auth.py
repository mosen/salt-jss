# -*- coding: utf-8 -*-
'''
Manage JAMF Pro Instances.

Authentication and Authorization related states.

- account (JSS accounts)
- ldap_server
- sso settings
- sso certificate

Dependencies
============

- python-jss (testing branch currently).

'''
from __future__ import absolute_import, print_function, unicode_literals
import logging
from xml.etree import ElementTree

from salt.exceptions import (
    CommandExecutionError, MinionError, SaltInvocationError
)
import salt.utils.platform

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
    '''This module only works using proxy minions.'''
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


def ldap_server(name,
                hostname,
                port,
                server_type,
                authentication_type,
                **kwargs):
    '''
    Ensure that the given ldap server is present.

    name
        Display name of the LDAP Server

    hostname
        The hostname to connect to

    port
        The ldap port, default is 389

    server_type
        "Active Directory", "Open Directory", "eDirectory" or "Custom"

    authentication_type
        "simple", "CRAM-MD5", "DIGEST-MD5", "none"

    *Optional:*

    use_ssl
        Use LDAPS protocol


    '''
    j = _get_jss()
    ret = {'name': name, 'result': False, 'changes': {}, 'comment': ''}
    changes = {'old': {}, 'new': {}}
    required_properties = ['hostname', 'port', 'authentication_type', 'server_type']
    connection_properties = ['authentication_type', 'open_close_timeout',
                             'search_timeout', 'referral_response', 'use_wildcards', 'connection_is_used_for']
    kwargs['connection_is_used_for'] = 'users'  # This seems to be always static

    try:
        ldap_server = j.LDAPServer(name)
        connection_el = ldap_server.find('connection')
    except jss.GetError as e:
        ldap_server = jss.LDAPServer(j, name)
        connection_el = ElementTree.SubElement(ldap_server, 'connection')

    required_values = {
        'hostname': hostname,
        'port': str(port),
        'server_type': server_type,
        'authentication_type': authentication_type
    }

    # Required properties
    for req_prop in required_properties:
        el = connection_el.find(req_prop)
        if el is None:
            el = ElementTree.SubElement(connection_el, req_prop)

        el.text = required_values[req_prop]
        changes['new'][req_prop] = required_values[req_prop]

    # Optional properties
    for conn_prop in connection_properties:
        if conn_prop not in kwargs:
            continue  # Didnt specify something, no change can occur

        el = connection_el.find(conn_prop)
        if el is None:
            el = ElementTree.SubElement(connection_el, conn_prop)

        if el.text != kwargs[conn_prop]:
            changes['old'] = connection_el.text
            el.text = kwargs[conn_prop]
            changes['new'] = kwargs[conn_prop]

    ldap_server.save()
    ret['changes'] = changes
    ret['result'] = True

    return ret


def account(name,
            **kwargs
    ):
    '''
    Ensure that the specified JSS Account is present on the server.

    TODO: Individual privileges are omitted for now.

    name
        The account name, which is unique to this JAMF Pro Server.

    full_name
        The users full name, used in display fields.

    email
        The users e-mail address.

    force_password_change
        Force a password change on next login.

    access_level
        Access level to give to this user, one of: 'Full Access', 'Site Access', 'Group Access'. Default is Full Access.
    '''
    j = _get_jss()
    ret = {'name': name, 'result': False, 'changes': {}, 'comment': ''}
    changes = {'old': {}, 'new': {}}
    created = False

    access_levels = ['Full Access', 'Site Access', 'Group Access']
    privilege_sets = ['Administrator', 'Auditor', 'Enrollment Only', 'Custom']

    optional_properties = ['full_name', 'email']

    try:
        jss_account = j.Account(name)
        account_el = jss_account.find('account')
    except jss.GetError as e:
        jss_account = jss.Account(j, name)
        account_el = ElementTree.SubElement(jss_account, 'account')
        changes['new']['name'] = name
        created = True

    if 'access_level' in kwargs:
        pass

    for p in optional_properties:
        if p not in kwargs:
            continue

        el = account_el.find(p)
        if el is None:
            el = ElementTree.SubElement(account_el, p)

        if el.text != kwargs[p]:
            changes['old'] = account_el.text
            el.text = kwargs[p]
            changes['new'] = kwargs[p]

    jss_account.save()

    if created:
        changes['new']['id'] = jss_account.findtext('id')

    ret['changes'] = changes
    ret['result'] = True

    return ret

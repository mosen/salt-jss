# Import Python libs
from __future__ import absolute_import, print_function, unicode_literals
import logging
import salt.utils
from xml.etree import ElementTree
from salt.exceptions import (
    CommandExecutionError, MinionError, SaltInvocationError
)
from xml.sax.saxutils import escape

# python-jss
HAS_LIBS = False
try:
    import jss
    from jss import jssobjects
    HAS_LIBS = True
except ImportError:
    pass

__virtualname__ = 'jamf_system'

logger = logging.getLogger(__name__)


def __virtual__():
    if not HAS_LIBS:
        return (
            False,
            'The following dependencies are required to use the jss modules: '
            'python-jss'
        )

    return __virtualname__


from jamf import _get_jss


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

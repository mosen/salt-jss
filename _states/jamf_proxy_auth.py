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


def _list_member_to_flag(items, member, flag_name, old_value):
    '''If `member` appears in `items`, then flag_name is equal to TRUE, else false.
    This helps us re-model long lists of flags as pure lists where the presence of the item denotes that it is
    enabled


    '''
    added = {}
    removed = {}
    if member in items:
        added[flag_name] = True
        if old_value is False:
            removed[flag_name] = False
    else:
        added[flag_name] = False
        if old_value is True:
            added[flag_name] = True

    return added, removed


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


def sso_settings(name,
                 entity_id,
                 user_mapping,
                 group_attribute_name,
                 group_rdn_key,
                 use_for,
                 metadata,
                 metadata_source='FILE',
                 metadata_filename='idp_metadata.xml',
                 user_attribute_name=None,
                 **kwargs):
    '''
    Ensure that Single-Sign on settings match the desired properties.

    TODO: This is only a partial implementation of the SSO Setting object.

    name
        The type of provider being used, you can specify any one of these presets:
            - Active Directory Federation Services
            - Okta
            - Google
            - Shibboleth
            - One Login
            - Ping Identity
            - Centrify

        If the name of the IdP does not match these strings exactly, the type will be set to "Other", and the name
        specified in "Other Provider:".

    entity_id
        The SAML SP Entity Id. This can be autogenerated to be the URL of the JAMF Service.

    user_mapping
        The attribute in JAMF that the assertion will be mapped to. Can be one of ["USERNAME", "EMAIL"]

    group_attribute_name
        The name of the SAML Assertion Attribute that contains group membership(s).

    group_rdn_key
        The Relative Distinguished Name key to extract group name from the LDAP string (e.g. "CN" or "DC")

    use_for
        A list of services that will require SSO, which can be any combination of:
            ["enrollment", "jss", "self_service"]

    session_timeout
        The number of minutes until the SAML token will expire.

    metadata
        A string containing the base64 encoded SAML IdP Metadata. Required if metadata_source is FILE

    metadata_source : FILE
        The source of the SAML IdP Metadata. Can be one of ["FILE", "URL"]

    metadata_filename : idp_metadata.xml
        The filename of the uploaded SAML IdP Metadata.

    user_attribute_name : None
        If specified, the username is not derived from the NameID in the SAML assertion but the attribute that matches
        this value.
    '''
    j = _get_jss()
    ret = {'name': name, 'result': False, 'changes': {}, 'comment': '', 'pchanges': {}}
    changes = {'old': {}, 'new': {}}
    provider_types = ['ADFS', 'OKTA', 'GOOGLE', 'SHIBBOLETH', 'ONELOGIN', 'PING', 'CENTRIFY']
    jamf_user_mappings = ['USERNAME', 'EMAIL']
    use_for = ['enrollment', 'jss', 'self_service']

    if len(use_for) > 0 and 'jss' not in use_for:
        raise SaltInvocationError('"jss" must be listed in sso_settings "use_for" argument if enabling enrollment or '
                                  'self_service')

    # Match a mixed-case provider name to a preset.
    provider_type = 'OTHER'
    provider_name = name
    for pt in provider_types:
        if name.upper() == pt:
            provider_type = pt
            break

    sso = j.uapi.SSOSetting()

    # Detect a change in provider or provider name
    if sso['idpProviderType'] != provider_type:
        changes['old']['name'] = sso['idpProviderType']

        if provider_type == 'OTHER':
            changes['new']['name'] = provider_name
            sso['idpProviderType'] = 'OTHER'
            sso['otherProviderTypeName'] = provider_name
        else:
            changes['new']['name'] = provider_type
            sso['idpProviderType'] = provider_type

    changes['old']['use_for'] = []
    changes['new']['use_for'] = []
    if 'jss' not in use_for:  # Effectively SSO is disabled.
        if sso['isEnabledJss'] is True:
            changes['old']['use_for'].append('jss')
            sso['isEnabledJss'] = False
    else:
        if sso['isEnabledJss'] is False:
            changes['new']['use_for'].append('jss')
            sso['isEnabledJss'] = True

        # added, removed = _list_member_to_flag(use_for, 'enrollment', 'isEnabledEnrollment', sso['isEnabledEnrollment'])
        # sso.update(added)

        if 'enrollment' in use_for and sso['isEnabledEnrollment'] is False:
            changes['new']['use_for'].append('enrollment')
            sso['isEnabledEnrollment'] = True
        elif 'enrollment' not in use_for and sso['isEnabledEnrollment'] is True:
            changes['old']['use_for'].append('enrollment')
            sso['isEnabledEnrollment'] = False

        if 'self_service' in use_for and sso['isEnabledOsx'] is False:
            changes['new']['use_for'].append('self_service')
            sso['isEnabledOsx'] = True
        elif 'self_service' not in use_for and sso['isEnabledOsx'] is True:
            changes['old']['use_for'].append('self_service')
            sso['isEnabledOsx'] = False

    if sso['entityID'] != entity_id:
        changes['old']['entity_id'] = sso['entityID']
        sso['entityID'] = entity_id
        changes['new']['entity_id'] = entity_id

    if 'allow_bypass' in kwargs and sso['isEnabledBypass'] != kwargs['allow_bypass']:
        sso['isEnabledBypass'] = (kwargs['allow_bypass'].upper() == 'TRUE')

    if user_attribute_name is not None:
        if sso['isUserAttributeEnabled'] is False:
            changes['old']['user_attribute_name'] = None
            sso['isUserAttributeEnabled'] = True
            sso['userAttributeName'] = user_attribute_name
            changes['new']['user_attribute_name'] = user_attribute_name
        elif sso['userAttributeName'] != user_attribute_name:
            changes['old']['user_attribute_name'] = sso['userAttributeName']
            sso['userAttributeName'] = user_attribute_name
            changes['new']['user_attribute_name'] = user_attribute_name
        else:
            pass  # no change

    if __opts__['test'] is True:
        ret['comment'] = 'The state of SSO Settings "{0}" will be changed.'.format(name)
        ret['pchanges'] = changes
        ret['result'] = None

        return ret
    else:
        sso.save()
        if len(changes['new'].keys()) > 0:
            ret['comment'] = 'SSO Settings have been updated'
            ret['changes'] = changes
        else:
            ret['comment'] = 'SSO Settings are in the correct state'

        ret['result'] = True

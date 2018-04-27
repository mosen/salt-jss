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

__virtualname__ = 'jamf'

logger = logging.getLogger(__name__)


def __virtual__():
    if not HAS_LIBS:
        return (
            False,
            'The following dependencies are required to use the jss modules: '
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


def activation_code():
    '''
    Retrieve the current activation details.

    CLI Example:

    .. code-block:: bash

        salt-call jss.activation_code
    '''
    j = _get_jss()
    try:
        activation_code = j.ActivationCode()
    except jss.JSSGetError as e:
        raise CommandExecutionError(
            'Unable to retrieve Activation Code, {0}'.format(e.message)
        )

    return {
        'organization_name': activation_code.findtext('organization_name'),
        'code': activation_code.findtext('code'),
    }


def list_ldap_servers():
    '''
    Retrieve a list of configured LDAP servers

    CLI Example:

    .. code-block:: bash

        salt-call jss.list_ldap_servers
    '''
    j = _get_jss()
    try:
        ldap_servers = j.LDAPServer()
    except jss.JSSGetError as e:
        raise CommandExecutionError(
            'Unable to retrieve LDAP server(s), {0}'.format(e.message)
        )

    return ldap_servers


def script(name=None, id=None):
    '''
    Retrieve a single script object from the JSS.

    You must use either the name or the id to reference a script, but not both.

    name
        (string) - The unique script name
    id
        (integer) - The script id

    CLI Example:

    .. code-block:: bash

        salt-call jss.script 'Script Name'

    '''
    j = _get_jss()
    try:
        script = j.Script(name)
        return script
    except jss.JSSGetError as e:  # TODO: Check 404 only (not 500)
        logging.debug('No such script found: {}'.format(name))
        return None


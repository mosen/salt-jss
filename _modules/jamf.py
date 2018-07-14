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
from xml.etree import ElementTree
import salt.utils.locales
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

        salt-call jamf.list_ldap_servers
    '''
    j = _get_jss()
    try:
        ldap_servers = j.LDAPServer()
    except jss.JSSGetError as e:
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
    if id is None and name is None:
        raise SaltInvocationError('You must provide either a name or id parameter')

    j = _get_jss()
    try:
        script = j.Script(name)
        return script
    except jss.JSSGetError as e:
        raise CommandExecutionError(
            'Unable to retrieve script(s), {0}'.format(e.message)
        )


def manage_script(name,
                  sfn,
                  ret,
                  source,
                  source_sum,
                  saltenv,
                  backup=None,
                  template=None,
                  show_changes=True,
                  contents=None,
                  skip_verify=False,
                  **kwargs):
    '''
    Check the destination against information retrieved by get_managed and make modifications if necessary.
    Derived from file.manage_file

    name
        unique script name in jamf pro server

    sfn
        location of cached file on the minion

        This is the path to the file stored on the minion. This file is placed
        on the minion using cp.cache_file.  If the hash sum of that file
        matches the source_sum, we do not transfer the file to the minion
        again.

        This file is then grabbed and if it has template set, it renders the
        file to be placed into the correct place on the system using
        salt.files.utils.copyfile()

    ret
        The initial state return data structure. Pass in ``None`` to use the
        default structure.

    source
        file reference on the master

    source_sum
        sum hash for source

        template
        format of templating

    show_changes
        Include diff in state return

    contents:
        contents to be placed in the file

    skip_verify : False
        If ``True``, hash verification of remote file sources (``http://``,
        ``https://``, ``ftp://``) will be skipped, and the ``source_hash``
        argument will be ignored.


    '''
    if not ret:
        ret = {'name': name,
               'changes': {},
               'comment': '',
               'result': True}

    # Ensure that user-provided hash string is lowercase
    if source_sum and ('hsum' in source_sum):
        source_sum['hsum'] = source_sum['hsum'].lower()

    if source:
        if not sfn:
            # File is not present, cache it
            sfn = __salt__['cp.cache_file'](source, saltenv)
            if not sfn:
                raise CommandExecutionError('Source file \'{0}\' not found'.format(source))

            htype = source_sum.get('hash_type', __opts__['hash_type'])
            # Recalculate source sum now that file has been cached
            source_sum = {
                'hash_type': htype,
                'hsum': __salt__['file.get_hash'](sfn, form=htype)
            }

    j = _get_jss()
    try:
        script = j.Script(name)
    except jss.GetError:
        # no such script
        script = None

    if script is not None:
        name_contents = script.find('script_contents').text
        name_sum = None

        if name_contents is not None:
            if __opts__['hash_type'] == 'sha256':
                name_sum = sha256_digest(name_contents)
            else:
                name_sum = sha256_digest(name_contents)

        if source is not None:
            print('using source')
            if name_sum is None or source_sum.get('hsum', __opts__['hash_type']) != name_sum:
                print('needs update')
                # Print a diff equivalent to diff -u old new
                if __salt__['config.option']('obfuscate_templates'):
                    ret['changes']['diff'] = '<Obfuscated Template>'
                elif not show_changes:
                    ret['changes']['diff'] = '<show_changes=False>'
                else:
                    ret['changes']['diff'] = 'thee should be a diff here'
                    # try:
                    #     ret['changes']['diff'] = get_diff(
                    #         real_name, sfn, show_filenames=False)
                    # except CommandExecutionError as exc:
                    #     ret['changes']['diff'] = exc.strerror

                try:
                    sfn_contents = __salt__['cp.get_file_str'](sfn)
                    print(sfn_contents)
                    script.add_script(sfn_contents)
                    script.save()
                except:
                    raise CommandExecutionError('cant save script update')
        elif contents is not None:
            # do a simple string comparison to check for changes
            ret['changes']['diff'] = 'needs to be a diff here'
            script.add_script(contents)
            script.save()

        if ret['changes']:
            ret['comment'] = 'Script {0} updated'.format(
                salt.utils.locales.sdecode(name)
            )

        elif not ret['changes'] and ret['result']:
            ret['comment'] = 'Script {0} is in the correct state'.format(
                salt.utils.locales.sdecode(name)
            )

        return ret
    else:  # target script does not exist
        script = jss.Script(j, name)

        if source is not None:
            ret['changes']['diff'] = 'New script'
            sfn_contents = __salt__['cp.get_file_str'](sfn)
            script.add_script(sfn_contents)
        else:
            if contents is None:
                ret['changes']['new'] = 'Script {0} created'.format(name)
                ret['comment'] = 'Empty script'
            else:
                ret['changes']['diff'] = 'New script'
                script.add_script(contents)

        script.save()
        return ret

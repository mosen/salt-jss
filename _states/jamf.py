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

    logger.debug('Using JAMF Pro URL: {}'.format(jss_options['url']))

    j = jss.JSS(
        url=jss_options['url'],
        user=jss_options['username'],
        password=jss_options['password'],
        ssl_verify=jss_options['ssl_verify'],
    )

    return j


def category(name,
             priority='9'):
    '''
    Ensure that the given category is present.

    name
        Name of the category

    priority
        Self-Service priority, default is 9
    '''
    j = _get_jss()
    ret = {'name': name, 'result': False, 'changes': {}, 'comment': ''}
    changes = {'old': {}, 'new': {}}

    try:
        category = j.Category(name)

        current_priority = category.find('priority').text
        if current_priority != priority:
            changes['old']['priority'] = current_priority
            category.find('priority').text = str(priority)
            changes['new']['priority'] = str(priority)
            category.save()
            ret['result'] = True

    except jss.GetError as e:
        category = jss.Category(j, name)
        priority_el = ElementTree.SubElement(category, 'priority')
        priority_el.text = str(priority)
        changes['new']['name'] = name
        changes['new']['priority'] = str(priority)
        category.save()
        ret['result'] = True

    ret['changes'] = changes
    return ret


def site(name):
    '''
    Ensure that the given site is present.

    name
        Name of the site
    '''
    j = _get_jss()
    ret = {'name': name, 'result': False, 'changes': {}, 'comment': ''}
    changes = {'old': {}, 'new': {}}

    try:
        site = j.Site(name)
        ret['result'] = True

    except jss.GetError as e:
        site = jss.Site(j, name)
        changes['new']['name'] = name
        site.save()
        ret['changes'] = changes
        ret['result'] = True

    return ret


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
    required_properties = ['name', 'hostname', 'port', 'authentication_type', 'server_type']
    connection_properties = ['authentication_type', 'open_close_timeout', 'use_ssl',
                             'search_timeout', 'referral_response', 'use_wildcards', 'connection_is_used_for']
    kwargs['connection_is_used_for'] = 'users'  # This seems to be always static

    try:
        ldap_server = j.LDAPServer(name)
        connection_el = ldap_server.find('connection')
    except jss.GetError as e:
        ldap_server = jss.LDAPServer(j, name)
        connection_el = ElementTree.SubElement(ldap_server, 'connection')

    required_values = {
        'name': name,
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

        old_value = el.text
        el.text = str(required_values[req_prop])

        if old_value != el.text:
            changes['old'][req_prop] = old_value
            changes['new'][req_prop] = required_values[req_prop]

    if authentication_type != "none":
        if 'distinguished_username' not in kwargs or 'password' not in kwargs:
            raise SaltInvocationError(
                'cannot specify an authentication type if you do not supply a distinguished_username and password, '
            )

        account_el = connection_el.find('account')
        if account_el is None:
            account_el = ElementTree.SubElement(connection_el, 'account')
            dn_el = ElementTree.SubElement(account_el, 'distinguished_username')
            dn_el.text = kwargs['distinguished_username']
            pw_el = ElementTree.SubElement(account_el, 'password')
            pw_el.text = kwargs['password']
        else:
            dn_el = account_el.find('distinguished_username')
            dn_el.text = kwargs['distinguished_username']
            # TODO

    # Optional properties
    for conn_prop in connection_properties:
        if conn_prop not in kwargs:
            continue  # Didnt specify something, no change can occur

        el = connection_el.find(conn_prop)
        if el is None:
            el = ElementTree.SubElement(connection_el, conn_prop)

        if el.text != kwargs[conn_prop]:
            changes['old'][conn_prop] = connection_el.text
            if isinstance(kwargs[conn_prop], bool):
                el.text = 'true' if kwargs[conn_prop] else 'false'
            else:
                el.text = str(kwargs[conn_prop])
            changes['new'][conn_prop] = kwargs[conn_prop]

    user_mappings_args = {
        'object_classes': '',
        'search_base': 'search_base',
        'search_scope': 'search_scope',
    }

    # user_mapping_args = {
    #     'user_id': 'map_user_id',
    #     'username': 'map_username',
    #     'realname': 'map_realname',
    #     'email_address'
    # }

    ldap_server.save()
    ret['changes'] = changes
    ret['result'] = True

    return ret


def script(name,
           # From file.managed:
           source=None,
           source_hash='',
           source_hash_name=None,
           template=None,
           contents=None,
           context=None,
           defaults=None,
           skip_verify=True,
           **kwargs):
    '''
    Ensure that given script is present.

    This state inherits a lot of behaviour from ``file.managed`` to support non-local file sources.


    source
        Managed file source, exactly the same rules as ``file.managed`` as per the excerpt below:

            The source file to download to the minion, this source file can be
            hosted on either the salt master server (``salt://``), the salt minion
            local file system (``/``), or on an HTTP or FTP server (``http(s)://``,
            ``ftp://``).

            If the file is hosted on a HTTP or FTP server then the source_hash
            argument is also required.

        This is a stripped down implementation of the same function, so the following restrictions apply:

        - No user or group ownership as we are dealing with a remote resource not a filesystem item.


    name
        Name of the script (must be unique for the entire jss instance).

    category
        Category

    filename
        Filename

    info
        Information

    notes
        Notes

    contents
        Script contents inline

    template
        If this setting is applied then the named templating engine will be
        used to render the downloaded file. Currently, jinja and mako are
        supported.



    **Example:**

    .. code-block:: yaml
        name_or_unique_id:
          jamf.script:
            - name: Script Name
            - category: Category Name
            - filename: filename.sh
            - info: Script information
            - notes: Script notes
            - priority: Before | After | reboot
            - parameters:
              - p4
              - p5
              - p6
            - os_requirements: 10.13.x
            - contents: |
                inline content or
            - source: ./path/to/script.sh
            - source_hash: ''
            - source_hash_name:
    '''
    j = _get_jss()
    script_attrs = ['filename', 'info', 'notes', 'os_requirements', 'priority']  # Treated verbatim

    logger.debug("Searching for existing script with name: {}".format(name))
    ret = {'name': name, 'result': False, 'changes': {}, 'comment': ''}
    changes = {'old': {}, 'new': {}}

    try:
        script = j.Script(name)  # Script exists, but may be different.
    except jss.GetError as e:
        script = jss.Script(j, name)  # Script does not exist

    # Basic attributes
    for attr in script_attrs:
        if attr not in kwargs:
            continue  # Don't check for changes on non specified attributes

        logger.debug('Checking element {}'.format(attr))
        attr_el = script.find(attr)

        if attr_el is not None and attr_el.text != kwargs[attr]:
            changes['old'][attr] = script.find(attr).text
            script.find(attr).text = kwargs[attr]
            changes['new'][attr] = kwargs[attr]
        elif attr_el is None:
            attr_el = ElementTree.SubElement(script, attr)
            attr_el.text = kwargs[attr]
            changes['new'][attr] = kwargs[attr]

    # Category
    if 'category' in kwargs:
        category_el = script.find('category')
        if category_el is None:
            category_el = ElementTree.SubElement(script, 'category')

        if category_el.text != kwargs['category']:
            changes['old']['category'] = category_el.text
            category_el.text = kwargs['category']
            changes['new']['category'] = kwargs['category']

    # Parameters
    if len(kwargs.get('parameters', [])) > 0:
        for p in range(4, 11):
            parameter = 'parameter{}'.format(p)

            if p - 4 >= len(kwargs['parameters']):
                break  # No more parameters to process

            parameter_el = script.find(parameter)
            if parameter_el is None:
                parameter_el = ElementTree.SubElement(script, parameter)

            if parameter_el.text != kwargs['parameters'][p - 4]:
                parameter_el.text = kwargs['parameters'][p - 4]
                changes['new'][parameter] = kwargs['parameters'][p - 4]

    # Contents
    if source and contents is not None:
        raise SaltInvocationError(
            '\'source\' cannot be used in combination with \'contents\', '
        )

    current_script_contents = script.find('script_contents')

    if contents is not None:
        if current_script_contents is not None:
            changes['old']['contents'] = script.find('script_contents').text

        # script.add_script(contents)  # Will be XML encoded
        escaped_script_contents = escape(contents)
        if current_script_contents is None:
            script_contents_tag = ElementTree.SubElement(
                script, "script_contents")
            script_contents_tag.text = escaped_script_contents

        changes['new']['contents'] = contents

    elif source is not None:
        # Normally, in file.managed, a more complex workflow is used:
        # file.managed calls a bunch of other modules:
        # - file.source_list evaluates a list of sources for the first existing item
        # - file.get_managed `gathers` the source file from the server, we can't use this because it expects
        #   a destination file to check against a checksum, so we have to break it down into cp.* calls and perform
        #   our own hashing.

        # If the source is a list then find which file exists.
        # NOTE: source_hash is not always present
        source, source_hash = __salt__['file.source_list'](
            source,
            source_hash,
            __env__
        )

        # file.get_managed will retrieve the data if its a template, or if it is remote (http, ftp, sftp, s3) but
        # somehow a remote salt:// file doesn't even count and sfn is empty in that case
        sfn, source_sum, comment_ = __salt__['file.get_managed'](
            name,
            None,  # if template is None sfn is None??
            source,
            source_hash,
            source_hash_name,
            0,
            0,
            755,
            None,
            'base',
            context,
            defaults,
            skip_verify=False,
            **kwargs
        )

        # sfn only guaranteed to exist if file is remote or template.
        # otherwise, just grab contents.
        # Here, we implement parts of file.manage_file because we don't need to deal with the filesystem really.
        ret = __salt__['jamf.manage_script'](
            name,
            sfn,
            ret,
            source,
            source_sum,
            __env__,
        )


        # current_script_contents = script.find('script_contents')
        # if current_script_contents is not None and current_script_contents.text is not None:
        #     changes['old']['contents'] = script.find('script_contents').text
        # else:
        #     current_script_contents = ElementTree.SubElement(script, 'script_contents')
        #
        # current_script_contents.text = script_contents
        # changes['new']['contents'] = script_contents

    if len(changes['old'].keys()) > 0 or len(changes['new'].keys()) > 0:
        ret['changes'] = changes  # Only show changes if there were any

    if __opts__['test']:
        ret['result'] = None
    else:
        script.save()
        ret['result'] = True

    return ret

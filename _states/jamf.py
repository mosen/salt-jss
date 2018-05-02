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

    except jss.JSSGetError as e:
        category = jss.Category(j, name)
        priority_el = ElementTree.SubElement(category, 'priority')
        priority_el.text = str(priority)
        changes['new']['name'] = name
        changes['new']['priority'] = str(priority)
        category.save()
        ret['result'] = True

    ret['changes'] = changes
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
    required_properties = ['hostname', 'port', 'authentication_type', 'server_type']
    connection_properties = ['authentication_type', 'open_close_timeout',
                             'search_timeout', 'referral_response', 'use_wildcards', 'connection_is_used_for']
    kwargs['connection_is_used_for'] = 'users'  # This seems to be always static

    try:
        ldap_server = j.LDAPServer(name)
        connection_el = ldap_server.find('connection')
    except jss.JSSGetError as e:
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


def script(name,
           source=None,
           source_hash='',
           source_hash_name=None,
           contents=None,
           template='jinja',
           context=None,
           defaults=None,
           skip_verify=True,
           **kwargs):
    '''
    Ensure that given script is present.

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

    source
        Managed file source

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
    except jss.JSSGetError as e:
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
        logger.debug('Retrieving from source {}'.format(source))

        script_tmp_file = salt.utils.files.mkstemp()
        current_script_contents = script.find('script_contents')
        if current_script_contents is not None and current_script_contents.text is not None:
            changes['old']['contents'] = script.find('script_contents').text

            with open(script_tmp_file, 'wb') as fd:
                fd.write(current_script_contents.text)
        else:
            current_script_contents = ElementTree.SubElement(script, 'script_contents')

        if __opts__['test']:
            fcm = __salt__['file.check_managed'](name=script_tmp_file,
                                                 source=source,
                                                 source_hash=source_hash,
                                                 source_hash_name=source_hash_name,
                                                 user=None,
                                                 group=None,
                                                 mode=None,
                                                 attrs=[],
                                                 template=template,
                                                 context=context,
                                                 defaults=defaults,
                                                 saltenv=__env__,
                                                 **kwargs
                                                 )
            ret['result'], ret['comment'] = fcm
        else:
            # If the source is a list then find which file exists
            source, source_hash = __salt__['file.source_list'](source,
                                                               source_hash,
                                                               __env__)

            # Gather the source file from the server
            try:
                fgm = __salt__['file.get_managed'](
                    name=script_tmp_file,
                    template=template,
                    source=source,
                    source_hash=source_hash_name,
                    source_hash_name=None,
                    user=None,
                    group=None,
                    mode=None,
                    attrs=[],
                    saltenv=__env__,
                    context=context,
                    defaults=defaults,
                    skip_verify=False,
                    **kwargs
                )
            except Exception as exc:
                ret['result'] = False
                ret['changes'] = {}
                ret['comment'] = 'Unable to manage file: {0}'.format(exc)
                return ret

            sfn, source_sum, comment = fgm
            if len(sfn) > 0:
                with open(sfn, 'rb') as fd:
                    current_script_contents.text = fd.read()

    if len(changes['old'].keys()) > 0 or len(changes['new'].keys()) > 0:
        ret['changes'] = changes  # Only show changes if there were any

    if __opts__['test']:
        ret['result'] = None
    else:
        script.save()
        ret['result'] = True

    return ret

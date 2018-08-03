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


def building(name):
    '''Ensure that a building is present.

    name
        Name of the building
    '''
    j = _get_jss()
    ret = {'name': name, 'result': False, 'changes': {}, 'comment': ''}
    changes = {'old': {}, 'new': {}}

    try:
        b = j.Building(name)
        ret['result'] = True
        return ret
    except jss.GetError as e:
        b = jss.Building(j, name)
        changes['comment'] = 'Object created'
        changes['new']['name'] = name
        return ret


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


def mac_configuration_profile(name,
                              # From file.managed:
                              source=None,
                              source_hash='',
                              source_hash_name=None,
                              contents=None,
                              context=None,
                              defaults=None,
                              skip_verify=True,
                              **kwargs):
    '''
    Ensure that the given mac configuration profile is present.

    This state inherits a lot of behaviour from ``file.managed`` to support non-local file sources.
    '''
    j = _get_jss()

    ret = {'name': name, 'result': False, 'changes': {'old': {}, 'new': {}}, 'comment': ''}

    # Contents
    if source and contents is not None:
        raise SaltInvocationError(
            '\'source\' cannot be used in combination with \'contents\', '
        )

    if source is not None:
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
        ret = __salt__['jamf_profiles.manage_mac_profile'](
            name,
            sfn,
            ret,
            source,
            source_sum,
            __env__,
            **kwargs
        )
    elif contents is not None:
        ret = __salt__['jamf_profiles.manage_mac_profile'](
            name,
            None,
            ret,
            None,
            None,
            __env__,
            contents=contents,
            **kwargs
        )

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

    logger.debug("Searching for existing script with name: {}".format(name))
    ret = {'name': name, 'result': False, 'changes': {'old': {}, 'new': {}}, 'comment': ''}

    # Contents
    if source and contents is not None:
        raise SaltInvocationError(
            '\'source\' cannot be used in combination with \'contents\', '
        )

    priority = kwargs.get('priority', None)
    if priority is not None:
        if priority not in ['After', 'Before', 'At Reboot']:
            raise SaltInvocationError(
                '\'priority\' must be one of: \'After\', \'Before\', or \'At Reboot\''
            )

    if source is not None:
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
        ret = __salt__['jamf_scripts.manage_script'](
            name,
            sfn,
            ret,
            source,
            source_sum,
            __env__,
            **kwargs
        )
    elif contents is not None:
        ret = __salt__['jamf_scripts.manage_script'](
            name,
            None,
            ret,
            None,
            None,
            __env__,
            contents=contents,
            **kwargs
        )

    return ret


def smart_computer_group(name,
                         criteria,
                         site=None,
                         **kwargs):
    '''Ensure that the given Computer Smart Group is present.

    name
        The unique name for the smart group. This is also used to determine whether the smart group already exists.

    criteria
        An array in the form of:

            - criteria:
              - Application Title:
                  is: AppCode.app
              - Application Version:
                  is_not: 2017.1.2

        With the key of each array describing the field to base the criteria on, and the value being the condition

    site
        The (optional) site name to be associated with the smart group.

    '''
    j = _get_jss()
    ret = {'name': name, 'result': False, 'changes': {'old': {}, 'new': {}}, 'comment': ''}
    is_new = False

    try:  # For now, we don't even compare criteria against the existing object. Just the existence of that object.
        grp = j.ComputerGroup(name)
        ret['result'] = None
        del ret['changes']['old']
        del ret['changes']['new']
    except jss.GetError as e:
        grp = jss.ComputerGroup(j, name)
        grp.find('is_smart').text = 'true'
        is_new = True

        criteria_el = grp.find('criteria')
        i = 0

        for cri in criteria:
            ret['changes']['new']['criteria'] = []
            new_change = {}
            for name, definition in cri.items():
                criterion_el = ElementTree.SubElement(criteria_el, 'criterion')
                name_el = ElementTree.SubElement(criterion_el, 'name')
                name_el.text = new_change['name'] = name
                priority_el = ElementTree.SubElement(criterion_el, 'priority')
                priority_el.text = new_change['priority'] = str(i)
                and_or_el = ElementTree.SubElement(criterion_el, 'and_or')
                and_or_el.text = new_change['and_or'] = 'and'
                search_type_el = ElementTree.SubElement(criterion_el, 'search_type')

                if 'is' in definition:
                    value = definition['is']
                    search_type_el.text = new_change['search_type'] = 'is'
                elif 'is_not' in definition:
                    value = definition['is_not']
                    search_type_el.text = new_change['search_type'] = 'is not'
                elif 'like' in definition:
                    value = definition['is_not']
                    search_type_el.text = new_change['search_type'] = 'like'
                elif 'not_like' in definition:
                    value = definition['not_like']
                    search_type_el.text = new_change['search_type'] = 'not like'
                elif 'has' in definition:
                    value = definition['has']
                    search_type_el.text = new_change['search_type'] = 'has'
                elif 'does_not_have' in definition:
                    value = definition['does_not_have']
                    search_type_el.text = new_change['search_type'] = 'does_not_have'
                elif 'before' in definition:  # Before specific date (YYYY-MM-DD)
                    value = definition['before']
                    search_type_el.text = new_change['search_type'] = 'before'
                elif 'after' in definition:  # After specific date (YYYY-MM-DD)
                    value = definition['after']
                    search_type_el.text = new_change['search_type'] = 'after'
                else:
                    raise SaltInvocationError('Unrecognised search type: {}'.format(definition))

                value_el = ElementTree.SubElement(criterion_el, 'value')
                value_el.text = new_change['value'] = value

                opening_paren_el = ElementTree.SubElement(criterion_el, 'opening_paren')
                opening_paren_el.text = 'false'
                closing_paren_el = ElementTree.SubElement(criterion_el, 'closing_paren')
                closing_paren_el.text = 'false'

                i += 1

                ret['changes']['new']['criteria'].append(new_change)
                new_change = {}

        grp.save()
        ret['result'] = True

    return ret


def policy(name,
           enabled=True,
           site=None,
           category=None,
           triggers=None,
           frequency='Once per computer',
           target_drive=None,
           limitations=None,

           scope=None,
           self_service=None,
           **kwargs):
    '''Ensure that the given Policy is present.

    The state will not create requisites for dependent objects, you will have to create your own requisites.

    name
        The unique name for the policy. This is also used to determine whether the policy already exists.

    enabled
        Whether the policy will be enabled or not

    site (optional)
        The name of an associated site.

    category (optional)
        The category that the policy will be featured in.

    triggers (optional)
        List of triggers including custom names that will trigger this policy.
        Reserved names are:
            - startup
            - login
            - logout
            - network_state_changed
            - enrollment_complete
            - checkin

    frequency (optional)
        Policy frequency, may be one of:
            - Once per computer
            - Once per user per computer
            - Once per user
            - Once every day
            - Once every week
            - Once every month
            - Ongoing

    target_drive (optional)
        Drive to run the policy against (defaults to the boot drive '/')

    limitations (optional)
        TBD

    scope (optional)
        TBD

    self_service (optional)
        TBD
    '''
    j = _get_jss()
    ret = {'name': name, 'result': False, 'changes': {}, 'comment': ''}
    changes = {'old': {}, 'new': {}}

    reserved_triggers = ['startup', 'login', 'logout', 'network_state_changed', 'enrollment_complete', 'checkin']
    old_triggers = set()

    try:
        pol = j.Policy(name)

        for rtrig in reserved_triggers:
            reserved_trigger_element = 'general/trigger_{}'.format(rtrig)
            reserved_trigger_etree = pol.find(reserved_trigger_element)

            if reserved_trigger_etree is not None:
                if reserved_trigger_etree.text == 'true':
                    old_triggers.add(rtrig)

        if pol.find('general/trigger_other') is not None:  # Custom trigger
            old_triggers.add(pol.findtext('general/trigger_other'))

    except jss.GetError:
        pol = jss.Policy(j, name)

    # Check Triggers
    if triggers is not None:
        changes['old']['triggers'] = list(old_triggers)
        triggers_remove = old_triggers - set(triggers)
        logging.debug('Triggers to remove: %s', triggers_remove)
        triggers_add = set(triggers) - old_triggers
        logging.debug('Triggers to add: %s', triggers_add)
        changes['new']['triggers'] = triggers

        for remove_trigger in triggers_remove:
            if remove_trigger in reserved_triggers:
                remove_trigger_el = pol.find('general/trigger_{}'.format(remove_trigger))
                if remove_trigger_el is not None and remove_trigger_el.text == 'true':
                    remove_trigger_el.text = 'false'
            else:
                pol.find('general/trigger_other').text = None

        for add_trigger in triggers_add:
            if add_trigger in reserved_triggers:
                add_trigger_el = pol.find('general/trigger_{}'.format(add_trigger))
                if add_trigger_el is not None and add_trigger_el.text == 'false':
                    add_trigger_el.text = 'true'
            else:
                pol.find('general/trigger_other').text = add_trigger





    pol.save()
    ret['result'] = True
    ret['changes'] = changes
    return ret

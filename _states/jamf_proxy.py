# -*- coding: utf-8 -*-
'''
Manage JAMF Pro Instances.

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
        ret = __salt__['jamf.manage_script'](
            name,
            sfn,
            ret,
            source,
            source_sum,
            __env__,
            **kwargs
        )
    elif contents is not None:
        ret = __salt__['jamf.manage_script'](
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
        ret['result'] = True
        ret['comment'] = 'Computer Smart Group already exists'
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


def package(name,
            category=None,
            filename=None,
            info=None,
            notes=None,
            **kwargs):
    '''Ensure that the given package object is present.

    Does not upload the package.
    '''
    j = _get_jss()
    ret = {'name': name, 'result': False, 'changes': {'old': {}, 'new': {}}, 'comment': ''}

    try:
        pkg = j.Package(name)
    except jss.GetError as e:
        pkg = jss.Package(j, name)

    if category is not None and category != pkg.category.text:
        ret['changes']['old']['category'] = pkg.category.text
        pkg.category.text = category
        ret['changes']['new']['category'] = category

    if filename is not None and filename != pkg.filename.text:
        ret['changes']['old']['filename'] = pkg.filename.text
        pkg.filename.text = filename
        ret['changes']['new']['filename'] = filename

    if info is not None and info != pkg.info.text:
        ret['changes']['old']['info'] = pkg.info.text
        pkg.info.text = info
        ret['changes']['new']['info'] = info

    if notes is not None and notes != pkg.notes.text:
        ret['changes']['old']['notes'] = pkg.notes.text
        pkg.notes.text = notes
        ret['changes']['new']['notes'] = notes

    try:
        pkg.save()
        ret['comment'] = 'Package updated successfully.'
        ret['result'] = True
        return ret
    except jss.PostError as e:
        ret['comment'] = 'Failed to save Package: {0}'.format(e.message)
        return ret
    except jss.PutError as e:
        ret['comment'] = 'Failed to update Package: {0}'.format(e.message)
        return ret


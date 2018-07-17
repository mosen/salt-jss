# -*- coding: utf-8 -*-
'''
Manage a JAMF Pro instance via the JAMF API

This module contains all execution module functions that relate to scripts and extension attributes.

:maintainer:    Mosen <mosen@noreply.users.github.com>
:maturity:      beta
:depends:       python-jss
:platform:      darwin
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
from jamf import _get_jss

# python-jss
HAS_LIBS = False
try:
    import jss
    HAS_LIBS = True
except ImportError:
    pass

__virtualname__ = 'jamf_scripts'

logger = logging.getLogger(__name__)


def __virtual__():
    if not HAS_LIBS:
        return (
            False,
            'The following dependencies are required to use the jss modules: '
            'python-jss'
        )

    return __virtualname__


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
                  category=None,
                  info=None,
                  notes=None,
                  os_requirements=None,
                  parameters=None,
                  priority=None,
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

    category:
        The unique name of the category that this script should be assigned to.

    info:
        The script administrator information

    notes:
        Notes to display about the script

    os_requirements:
        Comma separated list of supported operating systems

    parameters:
        List of parameters starting from parameter4 through 12.
    '''
    if not ret:
        ret = {'name': name,
               'changes': {'new': {}, 'old': {}},
               'comment': '',
               'result': True}

    def _ensure_element(parent, child_name, newvalue=None):
        '''Ensure that the sub element exists and has the value newvalue.

        Returns tuple of old value, new value. Or None if no change made'''
        if newvalue is not None:
            el = parent.find(child_name)
            old = None
            new = None

            if el is not None and el.text != newvalue:
                old = el.text
                new = newvalue
                el.text = newvalue
            elif el is None:
                el = ElementTree.SubElement(parent, child_name)
                new = newvalue
                el.text = newvalue

            return old, new
        else:
            return None, None

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
    is_new = False

    try:
        script = j.Script(name)
    except jss.GetError:
        # no such script
        script = jss.Script(j, name)
        is_new = True

    # Basics
    old_info, new_info = _ensure_element(script, 'info', info)
    if old_info or new_info:
        ret['changes']['old']['info'], ret['changes']['new']['info'] = old_info, new_info

    old_notes, new_notes = _ensure_element(script, 'notes', notes)
    if old_notes or new_notes:
        ret['changes']['old']['notes'], ret['changes']['new']['notes'] = old_notes, new_notes

    old_os_requirements, new_os_requirements = _ensure_element(script, 'os_requirements', os_requirements)
    if old_os_requirements or new_os_requirements:
        ret['changes']['old']['os_requirements'], ret['changes']['new']['os_requirements'] = old_os_requirements, new_os_requirements

    old_priority, new_priority = _ensure_element(script, 'priority', priority)
    if old_priority or new_priority:
        ret['changes']['old']['priority'], ret['changes']['new']['priority'] = old_priority, new_priority

    old_category, new_category = _ensure_element(script, 'category', category)
    if old_category or new_category:
        ret['changes']['old']['category'], ret['changes']['new']['category'] = old_category, new_category

    # Parameters
    if parameters is not None:
        parameters_el = script.find('parameters')
        if parameters_el is None:
            parameters_el = ElementTree.SubElement(script, 'parameters')

        for p in range(4, 12):
            parameter = 'parameter{}'.format(p)

            parameter_el = parameters_el.find(parameter)
            if parameter_el is None:
                parameter_el = ElementTree.SubElement(parameters_el, parameter)

            if p - 4 > len(parameters) - 1:
                ret['changes']['old'][parameter] = parameter_el.text
                ret['changes']['new'][parameter] = None
                parameter_el.text = None
            else:
                if parameter_el.text != parameters[p - 4]:
                    ret['changes']['old'][parameter] = parameter_el.text
                    parameter_el.text = parameters[p - 4]
                    ret['changes']['new'][parameter] = parameters[p - 4]

    if not is_new:
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
                print('needs update: {} vs {}'.format(source_sum.get('hsum', __opts__['hash_type']), name_sum))
                # Print a diff equivalent to diff -u old new
                if __salt__['config.option']('obfuscate_templates'):
                    ret['changes']['diff'] = '<Obfuscated Template>'
                elif not show_changes:
                    ret['changes']['diff'] = '<show_changes=False>'
                else:
                    pass

                try:
                    sfn_contents = __salt__['cp.get_file_str'](sfn)
                    ret['changes']['diff'] = ''.join(difflib.unified_diff(name_contents, sfn_contents, 'old {}'.format(name), 'new {}'.format(name)))
                    script.add_script(sfn_contents)
                    script.save()
                    ret['result'] = True
                except:
                    raise CommandExecutionError('cant save script update')
        elif contents is not None:
            if name_contents is not None:
                # do a simple string comparison to check for changes
                ret['changes']['diff'] = ''.join(difflib.unified_diff(name_contents, contents))
            else:
                ret['changes']['diff'] = contents

            script.add_script(contents)
            script.save()
            ret['result'] = True

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
        ret['result'] = True
        return ret


def manage_computer_ea(name,
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

                       description=None,
                       data_type='String',
                       input_type='Text Field',
                       inventory_display='Extension Attributes',
                       **kwargs):
    '''
    Check the destination against information retrieved by get_managed and make modifications if necessary.
    Derived from file.manage_file

    name
        unique ea display name in jamf pro server

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

    description
        Description of the Extension Attribute

    data_type
        The data type of the extension attribute, one of: String, Integer, Date

    input_type
        The input type of the extension attribute, one of: script, Text Field, LDAP Mapping, Pop-up Menu

    inventory_display
        Where the extension attribute will be displayed, one of: General, Hardware, Operating System, User and Location,
        Purchasing, Extension Attributes
    '''
    if not ret:
        ret = {'name': name,
               'changes': {'new': {}, 'old': {}},
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
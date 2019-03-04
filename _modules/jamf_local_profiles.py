# -*- coding: utf-8 -*-
'''
Manage a JAMF Pro instance via the JAMF API

This module contains all execution module functions that relate to configuration profiles on mac and ios

:maintainer:    Mosen <mosen@noreply.users.github.com>
:maturity:      beta
:depends:       python-jss
:platform:      darwin
'''
import logging
import os
import difflib
import plistlib
from xml.etree import ElementTree
from xml.sax.saxutils import unescape
import salt.utils.locales
import salt.utils.data
from salt.exceptions import (
    CommandExecutionError, MinionError, SaltInvocationError
)
import salt.utils.platform
# can't use get_hash because it only operates on files, not buffers/bytes
from salt.utils.hashutils import md5_digest, sha256_digest, sha512_digest


# python-jss
HAS_LIBS = False
try:
    import jss

    HAS_LIBS = True
except ImportError:
    pass

__virtualname__ = 'jamf_local_profiles'

logger = logging.getLogger(__name__)


def __virtual__():
    if not HAS_LIBS:
        return (
            False,
            'The following dependencies are required to use the jss modules: '
            'python-jss'
        )

    if salt.utils.platform.is_proxy():
        return (
            False,
            'jamf_local modules are not designed to run on proxy minions.'
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

def _ensure_element(parent, child_name, newvalue=None):
    '''Ensure that the sub element exists and has the value newvalue.

    Returns tuple of old value, new value. A value of None is returned if it never existed or has been removed.

    parent
        ElementTree.Element where the child will be added or updated

    child_name
        The tag name of the child, which is created if it does not exist

    newvalue
        The text value of the given child
    '''
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


def manage_mac_profile(
        name,
        sfn,
        ret,
        source,
        source_sum,
        saltenv,

        # osxconfigurationprofile
        # uuid will be calculated
        description=None,
        site=None,
        category=None,
        distribution_method='Install Automatically',
        user_removable=True,
        level='computer',
        redeploy_on_update='Newly Assigned',

        scope=None,

        **kwargs):
    '''
    Check the JAMF Pro Server against a local profile and make modifications if necessary.

    Derived from file.manage_file

    name
        unique profile name in jamf pro server

    sfn
        location of cached file on the minion

        This is the path to the file stored on the minion. This file is placed
        on the minion using cp.cache_file.  If the hash sum of that file
        matches the source_sum, we do not transfer the file to the minion
        again.

        This file is then grabbed and if it has template set, it renders the
        file to be placed into the correct place on the system using
        salt.files.utils.copyfile()

        The implementation is slightly different here since config profiles do not support templating.

    ret
        The initial state return data structure. Pass in ``None`` to use the
        default structure.

    source
        file reference on the master

    source_sum
        sum hash for source

    description
        Brief explanation of the content or purpose of the profile

    site
        Site to add the profile to (by name)

    category
        Category to add the profile to (by name)

    self_service
        Make available in self service instead of automatic installation

    user_removable
        User can remove the profile once installed

    level
        The scope of the profile, 'computer' or 'user'

    scope
        Ordered dict of scope options
    '''
    if not ret:
        ret = {'name': name,
               'changes': {'new': {}, 'old': {}},
               'comment': '',
               'result': True}

    # Ensure that user-provided hash string is lowercase
    if source_sum and ('hsum' in source_sum):
        source_sum['hsum'] = source_sum['hsum'].lower()

    if level:
        level = level.lower()

    # Cache file on minion (copy from master) if source is provided but sfn is not.
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
        profile = j.OSXConfigurationProfile(name)
    except jss.GetError:
        # no such script
        profile = jss.OSXConfigurationProfile(j, name)
        is_new = True

    # Basics
    old_desc, new_desc = _ensure_element(profile.find('general'), 'description', description)
    if old_desc or new_desc:
        ret['changes']['old']['description'], ret['changes']['new']['description'] = old_desc, new_desc

    if profile.find('general/category') is None or profile.findtext('general/category/name') != category:
        ret['changes']['old']['category'] = profile.findtext('general/category/name')
        profile.set_category(category)
        ret['changes']['new']['category'] = category

    old_distribution_method, new_distribution_method = _ensure_element(profile.find('general'), 'distribution_method',
                                                                       distribution_method)
    if old_distribution_method or new_distribution_method:
        ret['changes']['old']['distribution_method'], ret['changes']['new']['distribution_method'] = \
            old_distribution_method, new_distribution_method

    old_user_removable, new_user_removable = _ensure_element(profile.find('general'), 'user_removable',
                                                                       'true' if user_removable else 'false')
    if old_user_removable or new_user_removable:
        ret['changes']['old']['user_removable'], ret['changes']['new']['user_removable'] = \
            old_user_removable, new_user_removable

    old_level, new_level = _ensure_element(profile.find('general'), 'level', level)
    if old_level or new_level:
        ret['changes']['old']['level'], ret['changes']['new']['level'] = old_level, new_level

    # Scope
    if scope is not None:
        for scopeitem in scope:
            for k, v in scopeitem.items():
                if k == 'all_computers':
                    pass
                elif k == 'computer':
                    pass
                elif k == 'computer_group':
                    pass


    # Payload

    if not is_new:  # Cannot make a hash comparison, so generate a diff of PayloadUUIDs
        payloads = profile.findtext('general/payloads')
        if payloads is not None and source is not None:
            sfn_contents = __salt__['cp.get_file_str'](sfn)
            sfn_plist = plistlib.readPlistFromString(sfn_contents)
            sfn_payload_uuids = set([p['PayloadUUID'] for p in sfn_plist['PayloadContent']])

            payloads_plist = plistlib.readPlistFromString(payloads)
            existing_payload_uuids = set([p['PayloadUUID'] for p in payloads_plist['PayloadContent']])

            different_uuids = sfn_payload_uuids.difference(existing_payload_uuids)
            logger.debug("Different Payload UUIDs Found: %s", ", ".join(different_uuids))

            if len(different_uuids) > 0:
                profile.add_payloads(sfn_contents)
                ret['changes']['diff']['payload'] = 'Updated payload'
            else:
                ret['comment'] = 'Payload identical'
                ret['result'] = True

    else:
        if source is not None:
            ret['changes']['diff'] = 'New payload'
            sfn_contents = __salt__['cp.get_file_str'](sfn)

            profile.add_payloads(sfn_contents)
        else:
            ret['comment'] = 'Empty payload'

    profile.save()
    if len(ret['changes']['old'].keys()) == 0:
        del ret['changes']['old']

    if len(ret['changes']['new'].keys()) == 0:
        del ret['changes']['new']
        ret['result'] = None
    else:
        ret['result'] = True

    return ret


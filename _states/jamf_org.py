# -*- coding: utf-8 -*-
'''
Manage JAMF Pro Instances via Proxy Minion.

- Organisational Hierarchy (Categories, Departments, Buildings etc)

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


def _ensure_xml_str(parent, tag_name, desired_value):  # type: (ElementTree.Element, str, str) -> Tuple[str, str]
    '''Ensure that the given tag name exists, and has the desired value as its text. Return the difference as a tuple
    of old, new. No change = None, None'''
    child = parent.find(tag_name)
    if child is None:
        child = ElementTree.SubElement(parent, tag_name)

    old_value = child.text

    if old_value != desired_value:
        child.text = desired_value
        return old_value, desired_value
    else:
        return None, None


def _ensure_xml_bool(element, desired_value):  # type: (ElementTree.Element, bool) -> Tuple[str, str]
    '''Ensure that the given elements innertext matches the desired bool value. Return the difference as a tuple.
    No change = None, None'''
    if desired_value is None:  # Don't need to check for a change because the state did not specify a desired value.
        return None, None
    if (element.text == 'true') != desired_value:
        old_value = element.text == 'true'
        element.text = 'true' if desired_value else 'false'
        return old_value, desired_value
    else:
        return None, None


def building(name, **kwargs):
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

        current_priority = category.priority.text
        if current_priority != str(priority):
            changes['old']['priority'] = current_priority
            category.priority.text = str(priority)
            changes['new']['priority'] = str(priority)
            category.save()
            ret['result'] = True
        else:
            ret['comment'] = 'No changes required'
            ret['result'] = True

    except jss.GetError:
        category = jss.Category(j, name)
        priority_el = ElementTree.SubElement(category, 'priority')
        priority_el.text = str(priority)
        changes['new']['name'] = name
        changes['new']['priority'] = str(priority)
        category.save()
        ret['result'] = True

    if len(changes['new'].keys()) > 0:
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


def network_segment(
        name,
        ip_range=None,
        distribution_point=None,
):
    '''
    Ensure that the defined network segment is present.

    name
        The name of the Network Segment as displayed in the UI

    ip_range : None
        A list of two IPv4 addresses for the starting and ending address of the range.

    distribution_point : None
        The default Distribution Point for this Network Segment.
    '''
    j = _get_jss()
    ret = {'name': name, 'result': False, 'changes': {}, 'comment': ''}
    changes = {'old': {}, 'new': {}}
    # CLOUD_DISTRIBUTION_POINT = 'Cloud Distribution Point'

    if ip_range is not None and len(ip_range) != 2:
        raise SaltInvocationError(
            'Argument "ip_range" must be a list of two ipv4 addresses (start, end)'
        )

    segment = __salt__['jamf.network_segment'](name, as_object=True)
    if segment is None:
        segment = jss.NetworkSegment(j, name)

    if ip_range[0] != segment.findtext('starting_address'):
        try:
            changes['old']['starting_address'] = segment.starting_address.text
            segment.starting_address.text = ip_range[0]
        except AttributeError:
            starting_address_el = ElementTree.SubElement(segment, 'starting_address')
            starting_address_el.text = ip_range[0]

        changes['new']['starting_address'] = ip_range[0]

    if ip_range[1] != segment.findtext('ending_address'):
        try:
            changes['old']['ending_address'] = segment.ending_address.text
            segment.ending_address.text = ip_range[1]
        except AttributeError:
            ending_address_el = ElementTree.SubElement(segment, 'ending_address')
            ending_address_el.text = ip_range[1]

        changes['new']['ending_address'] = ip_range[1]

    if distribution_point != segment.findtext('distribution_point'):
        try:
            changes['old']['distribution_point'] = segment.distribution_point.text
            segment.distribution_point.text = distribution_point
        except AttributeError:
            distribution_point_el = ElementTree.SubElement(segment, 'distribution_point')
            distribution_point_el.text = distribution_point

        changes['new']['distribution_point'] = distribution_point

    if len(changes['new'].keys()) > 0:
        ret['changes'] = changes

        if __opts__['test']:
            ret['result'] = None
            ret['comment'] = '{0} would be modified'.format(name)
        else:
            try:
                segment.save()
                ret['result'] = True
                ret['comment'] = '{0} was updated'.format(name)
            except jss.PostError as e:
                ret['result'] = False
                ret['comment'] = 'Unable to save {0}, reason: {1}'.format(name, e.message)
    else:
        ret['comment'] = '{0} is already in the desired state'.format(name)
        ret['result'] = True

    return ret


def distribution_point(
        name,
        ip_address=None,
        is_master=None,
        connection_type=None,
        share_name=None,
        read_only_username=None,
        read_only_password=None,
        read_write_username=None,
        read_write_password=None
):
    '''
    Ensure that the defined Distribution Point is present.

    '''
    j = _get_jss()
    ret = {'name': name, 'result': False, 'changes': {}, 'comment': ''}
    changes = {'old': {}, 'new': {}}

    if connection_type not in ['SMB', 'AFP']:
        raise SaltInvocationError('Specified connection_type "{}" is not valid, must be one of: {}'.format(
            connection_type, ', '.join(['SMB', 'AFP']),
        ))

    try:
        dp = j.DistributionPoint(name)

    except jss.GetError:
        dp = jss.DistributionPoint(j, name)


    changes['old']['ip_address'], changes['new']['ip_address'] = \
        _ensure_xml_str(dp, 'ip_address', ip_address)

    if is_master is not None:
        if not hasattr(dp, 'is_master'):
            ElementTree.SubElement(dp, 'is_master')

        if is_master != dp.is_master.text:
            changes['old']['is_master'] = dp.is_master.text
            changes['new']['is_master'] = str(is_master)
            dp.is_master.text = str(is_master)

    changes['old']['connection_type'], changes['new']['connection_type'] = \
        _ensure_xml_str(dp, 'connection_type', connection_type)

    changes['old']['share_name'], changes['new']['share_name'] = \
        _ensure_xml_str(dp, 'share_name', share_name)

    changes['old']['read_only_username'], changes['new']['read_only_username'] = \
        _ensure_xml_str(dp, 'read_only_username', read_only_username)

    changes['old']['read_only_password'], changes['new']['read_only_password'] = \
        _ensure_xml_str(dp, 'read_only_password', read_only_password)

    changes['old']['read_write_username'], changes['new']['read_write_username'] = \
        _ensure_xml_str(dp, 'read_write_username', read_write_username)

    changes['old']['read_write_password'], changes['new']['read_write_password'] = \
        _ensure_xml_str(dp, 'read_write_password', read_write_password)

    if len(changes['new'].keys()) > 0:
        ret['changes'] = changes

        if __opts__['test']:
            ret['result'] = None
            ret['comment'] = '{0} would be modified'.format(name)
        else:
            try:
                dp.save()
                ret['result'] = True
                ret['comment'] = '{0} was updated'.format(name)
            except jss.PostError as e:
                ret['result'] = False
                ret['comment'] = 'Unable to save {0}, reason: {1}'.format(name, e.message)
    else:
        ret['comment'] = '{0} is already in the desired state'.format(name)
        ret['result'] = True

    return ret

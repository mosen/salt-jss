# Import Python libs
from __future__ import absolute_import, print_function, unicode_literals
import logging
from xml.etree import ElementTree
from salt.exceptions import (
    CommandExecutionError, MinionError, SaltInvocationError
)

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

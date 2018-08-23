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

# -*- coding: utf-8 -*-
'''
Manage a JAMF Pro instance via the JAMF API

This module contains all execution module functions that relate to organisational structure.

:maintainer:    Mosen <mosen@noreply.users.github.com>
:maturity:      beta
:depends:       python-jss
:platform:      darwin
'''
import logging
from salt.exceptions import (
    CommandExecutionError, MinionError, SaltInvocationError
)

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
            'The following dependencies are required to use the jamf modules: '
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


def category(name=None, id=None, as_object=False):
    '''Get a Category by ID or name.

    You must use either the name or the id to reference a category, but not both.

    name
        (string) - The unique category name
    id
        (integer) - The category id

    CLI Example:

    .. code-block:: bash

        salt-call jamf.category 'Category Name'
    '''
    if id is None and name is None:
        raise SaltInvocationError('You must provide either a name or id parameter')

    j = _get_jss()
    try:
        if name is not None:
            category = j.Category(name)
        else:
            category = j.Category(int(id))

        if as_object:
            return category
        else:
            category_dict = {
                'id': category.id,
                'name': category.name,
                'priority': category.priority.text,
            }
            return category_dict

    except jss.GetError as e:
        raise CommandExecutionError(
            'Unable to retrieve category(s), {0}'.format(e.message)
        )




def network_segments(as_object=False):
    '''Get a list of network segments.'''
    j = _get_jss()
    try:
        segments = j.NetworkSegment()
    except jss.GetError as e:
        raise CommandExecutionError(
            'Unable to retrieve network segment(s), {0}'.format(e.message)
        )

    def _build_ns_dict(ns):
        if as_object:
            return ns
        else:
            return {
                'id': ns.id,
                'name': ns.name,
                'starting_address': ns.starting_address.text,
                'ending_address': ns.ending_address.text,
            }

    return [_build_ns_dict(segment) for segment in segments]


def network_segment(name=None, id=None, as_object=False):
    '''Get a Network Segment by ID or name.

    You must use either the name or the id to reference a network segment, but not both.

    name
        (string) - The unique segment name
    id
        (integer) - The segment id

    CLI Example:

    .. code-block:: bash

        salt-call jamf.network_segment 'Segment Name'
        salt-call jamf.network_segment id=1
    '''
    if id is None and name is None:
        raise SaltInvocationError('You must provide either a name or id parameter')

    j = _get_jss()

    def _build_ns_dict(ns):
        if as_object:
            return ns
        else:
            return {
                'id': ns.id,
                'name': ns.name,
                'starting_address': ns.starting_address.text,
                'ending_address': ns.ending_address.text,
            }

    try:
        if name is not None:
            segment = j.NetworkSegment(name)
        else:
            segment = j.NetworkSegment(int(id))

        if as_object:
            return segment
        else:
            return _build_ns_dict(segment)

    except jss.GetError as e:
        return None


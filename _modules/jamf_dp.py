# -*- coding: utf-8 -*-
'''
Manage a JAMF Pro instance via the JAMF API

This module contains all execution module functions that relate to distribution points.

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


def distribution_points(as_object=False):
    '''Get a list of distribution points.'''
    j = _get_jss()
    try:
        dps = j.DistributionPoint()
    except jss.GetError as e:
        raise CommandExecutionError(
            'Unable to retrieve distribution point(s), {0}'.format(e.message)
        )

    def _build_dp_dict(dp):
        if as_object:
            return dp
        else:
            return {
                'name': dp.name,
                'id': dp.id
            }

    return [_build_dp_dict(dp) for dp in dps]


def distribution_point(name=None, id=None, as_object=False):
    '''Get a Distribution Point by ID or Name.

    You must use either the name or the id to reference a distribution point, but not both.

    name
        (string) - The unique distribution point name
    id
        (integer) - The distribution point id

    .. code-block:: bash

        salt-call jamf.distribution_point 'DP Name'
        salt-call jamf.distribution_point id=1
    '''
    if id is None and name is None:
        raise SaltInvocationError('You must provide either a name or id parameter')

    j = _get_jss()
    try:
        if name is not None:
            dp = j.DistributionPoint(name)
        else:
            dp = j.DistributionPoint(int(id))

        if as_object:
            return dp
        else:
            # return str(dp)
            dp_dict = {
                'id': dp.id,
                'name': dp.name,
                'ip_address': dp.ip_address.text,
                'is_master': dp.is_master.text,
                'connection_type': dp.connection_type.text,
                'share_name': dp.share_name.text,
            }
            return dp_dict

    except jss.GetError as e:
        raise CommandExecutionError(
            'Unable to retrieve script(s), {0}'.format(e.message)
        )

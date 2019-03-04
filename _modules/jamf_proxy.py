# Import Python libs
from __future__ import absolute_import, print_function, unicode_literals
import logging
from xml.etree import ElementTree

# Import Salt libs
from salt.exceptions import (
    CommandExecutionError, MinionError, SaltInvocationError
)
import salt.utils.platform


logger = logging.getLogger(__name__)

__proxyenabled__ = ['jamf']
__virtualname__ = 'jamf'

# python-jss
HAS_LIBS = False
try:
    import jss
    HAS_LIBS = True
except ImportError:
    pass


def __virtual__():
    '''
    Only work on proxy
    '''
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

# UAPI Methods

def alerts():
    '''Retrieve a list of Alert Notifications from the JAMF Pro Server.

    CLI Example:

    .. code-block:: bash

        salt '*' jamf.alerts
    '''
    j = _get_jss()
    alerts = j.uapi.AlertNotification()

    return [dict(alert) for alert in alerts]


def buildings():
    '''Retrieve a list of Building objects from the JAMF Pro Server.

    CLI Example:

    .. code-block:: bash

        salt '*' jamf.buildings
    '''
    j = _get_jss()
    buildings = j.uapi.Building()

    return [dict(building) for building in buildings]


def cache_settings():
    '''Retrieve cache settings from the JAMF Pro Server.

    CLI Example:

    .. code-block:: bash

        salt '*' jamf.cache_settings
    '''
    j = _get_jss()
    settings = j.uapi.Cache()
    return dict(settings)


# def categories():
#     '''Retrieve a list of Categories from the JAMF Pro Server.
#
#     CLI Example:
#
#     .. code-block:: bash
#
#         salt '*' jamf.categories
#     '''
#     j = _get_jss()
#     categories = j.uapi.Category()
#
#     return [dict(cat) for cat in categories]


# def checkin_settings():
#     '''Retrieve client check-in settings from the JAMF Pro Server.
#
#     CLI Example:
#
#     .. code-block:: bash
#
#         salt '*' jamf.checkin_settings
#     '''
#     j = _get_jss()
#     settings = j.uapi.ClientCheckIn()
#     return dict(settings)


# def departments():
#     '''Retrieve departments from the JAMF Pro Server.
#
#     CLI Example:
#
#     .. code-block:: bash
#
#         salt '*' jamf.departments
#     '''
#     j = _get_jss()
#     departments = j.uapi.Department()
#
#     return [dict(dept) for dept in departments]


# def enrollment_history():
#     '''Retrieve enrollment history from the JAMF Pro Server.
#
#     CLI Example:
#
#     .. code-block:: bash
#
#         salt '*' jamf.enrollment_history
#     '''
#     j = _get_jss()
#     history = j.uapi.EnrollmentHistory()
#
#     return [dict(item) for item in history]


# def enrollment_settings():
#     '''Retrieve enrollment settings from the JAMF Pro Server.
#
#
#     CLI Example:
#
#     .. code-block:: bash
#
#         salt '*' jamf.enrollment_settings
#     '''
#     j = _get_jss()
#     settings = j.uapi.EnrollmentSetting()
#
#     return dict(settings)


def mobile_devices():
    '''Retrieve mobile devices from the JAMF Pro Server.

    CLI Example:

    .. code-block:: bash

        salt '*' jamf.mobile_devices
    '''
    j = _get_jss()
    devices = j.uapi.MobileDevice()

    return [dict(device) for device in devices]


# def scripts():
#     '''Retrieve scripts from the JAMF Pro Server.
#
#     CLI Example:
#
#     .. code-block:: bash
#
#         salt '*' jamf.scripts
#     '''
#     j = _get_jss()
#     scripts = j.uapi.Script()
#
#     return [dict(script) for script in scripts]


def selfservice_settings():
    '''Retrieve self-service settings from the JAMF Pro Server.

    CLI Example:

    .. code-block:: bash

        salt '*' jamf.selfservice_settings
    '''
    j = _get_jss()
    settings = j.uapi.SelfServiceSettings()

    return dict(settings)


# def sites():
#     '''Retrieve sites from the JAMF Pro Server.
#
#     CLI Example:
#
#     .. code-block:: bash
#
#         salt '*' jamf.selfservice_settings
#     '''
#     j = _get_jss()
#     sites = j.uapi.Site()
#
#     return [dict(site) for site in sites]


# def users():
#     '''Retrieve users from the JAMF Pro Server.
#
#     CLI Example:
#
#     .. code-block:: bash
#
#         salt '*' jamf.users
#     '''
#     j = _get_jss()
#     users = j.uapi.User()
#
#     return [dict(user) for user in users]


# def vpp_accounts():
#     '''Retrieve a list of VPP accounts from the JAMF Pro Server.
#
#     CLI Example:
#
#     .. code-block:: bash
#
#         salt '*' jamf.vpp_accounts
#     '''
#     j = _get_jss()
#     admins = j.uapi.VPPAdminAccount()
#
#     return [dict(admin) for admin in admins]


# def vpp_subscriptions():
#     '''Retrieve a list of VPP subscriptions from the JAMF Pro Server.
#
#     CLI Example:
#
#     .. code-block:: bash
#
#         salt '*' jamf.vpp_subscriptions
#     '''
#     j = _get_jss()
#     subs = j.uapi.VPPSubscription()
#
#     return [dict(sub) for sub in subs]

# Classic API Methods

def account(id=None, username=None):
    '''Retrieve a single JAMF Pro user account from the JAMF Pro Server.

    You can use either the id or username to find an account.

    id
        The account ID of the user to find
    name
        The account username of the user to find.

    CLI Example:

    .. code-block:: bash

        salt '*' jamf.account id=1
        salt '*' jamf.account name=admin
    '''
    j = _get_jss()

    if id is not None:
        account = j.Account(id)
    elif username is not None:
        account = j.Account(username)
    else:
        raise CommandExecutionError(
            'Did not supply either `id` or `name` to query for.'
        )


def accounts():
    '''Retrieve a list of JSS Console User Accounts from the JAMF Pro Server.

    CLI Example:

    .. code-block:: bash

        salt '*' jamf.accounts
    '''
    j = _get_jss()
    accounts = j.Account()

    def user(obj):
        return {
            'id': obj.id.text,
            'name': obj.name.text,
        }

    # python-jss already queries the sub-element of `users` for us.
    return [user(obj) for obj in accounts]


def activation_code():
    '''Retrieve the activation details from the JAMF Pro Server.

    CLI Example:

    .. code-block:: bash

        salt '*' jamf.activation_code
    '''
    j = _get_jss()
    activation = j.ActivationCode()

    result = {
        'activation_code': activation.code.text,
        'organization': activation.organization_name.text,
    }

    return result


def _computer_general(element):
    # type: (ElementTree.Element) -> dict
    '''Convert an ElementTree.Element representing the `general` section of the computer object into a dict.'''
    general = element.find('general')
    props = ['name', 'ip_address', 'serial_number', 'jamf_version', 'report_date', 'mac_address', 'udid', 'mdm_capable']

    return {k: general.findtext(k) for k in props}


def computers():
    '''Retrieve a list of computers from the JAMF Pro Server'''
    j = _get_jss()
    computers = j.Computer()

    def result(o):  # type: (ElementTree.Element) -> dict
        logger.debug(o)
        computer = {}
        computer.update(_computer_general(o))

        return computer

    return [result(obj) for obj in computers]


def mobiledevice_commands():
    '''Retrieve a list of MDM Commands sent to Mobile Devices from the JAMF Pro Server.


    CLI Example:

    .. code-block:: bash

        salt '*' jamf.mobiledevice_commands
    '''
    j = _get_jss()
    commands = j.MobileDeviceCommand()

    def result(o):
        return {
            'id': o.id,
            # 'udid': o.udid.text,
            'command': o.command.text,
        }

    return [result(obj) for obj in commands]

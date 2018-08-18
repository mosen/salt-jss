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


def enrollment_settings(
        name,
        skip_certificate_install=None,
        management_username=None,
        management_password=None,
        create_management_account=None,
        enable_ssh=None,
        launch_self_service=None,
        sign_quickadd=None
):
    '''Ensure that enrollment settings match the desired state.

    skip_certificate_install (bool)
        Skip certificate installation during enrollment. (required if your JAMF Pro server is not trusted by default)

    management_username (string)
        The name of the management account username.

    management_password (string)
        The management user password. If not provided, the password will be set to random.

    create_management_account (bool)
        Create the management account during enrollment if it does not already exist.

    enable_ssh (bool)
        Enable SSH (Remote Login) on computers that have it disabled.

    launch_self_service (bool)
        Launch Self Service immediately after the user is enrolled.

    sign_quickadd (bool)
        Sign the QuickAdd package

    '''
    current_settings = __salt__['jamf_settings.get_enrollment']()
    new_settings = {
        'managementPassword': u'\uffff\uffff\uffff\uffff\uffff\uffff\uffff\uffff\uffff\uffff\uffff\uffff\uffff\uffff\uffff'}
    ret = {'name': name, 'result': False, 'changes': {}, 'comment': ''}
    changes = {'old': {}, 'new': {}}

    logger.debug(current_settings)

    if skip_certificate_install is not None and current_settings['isSingleProfile'] != skip_certificate_install:
        changes['old']['skip_certificate_install'] = current_settings['isSingleProfile']
        new_settings['isSingleProfile'] = skip_certificate_install
        changes['new']['skip_certificate_install'] = skip_certificate_install

    if len(new_settings.keys()) > 0:
        __salt__['jamf_settings.set_enrollment'](new_settings)

    ret['changes'] = changes
    return ret


def inventory_collection(
        name,
        local_users=None,
        home_directory_sizes=None,
        hidden_accounts=None,
        printers=None,
        services=None,
        mobile_last_backup=None,
        package_receipts=None,
        software_updates=None,
        ibeacon_regions=None,
        applications=None,
        fonts=None,
        plugins=None
):
    '''Ensure that Inventory Collection settings match the desired state.

    local_users (bool)
        Collect local user information

    home_directory_sizes (bool)
        Calculate home directory sizes

    hidden_accounts (bool)
        Collect hidden users

    printers (bool)
        Collect printers

    services (bool)
        Collect active services

    mobile_last_backup (bool)
        Collect last backup date/time for managed mobile devices that are synced to computers

    package_receipts (bool)
        Collect package receipts

    software_updates (bool)
        Collect available software updates

    ibeacon_regions (bool)
        Monitor available iBeacon regions

    applications (bool)
        Collect application usage information

    fonts (bool)
        Collect font information

    plugins (bool)
        Collect plugin information

    '''
    collection_prefs = __salt__['jamf_settings.get_inventory_collection'](as_object=True)
    ret = {'name': name, 'result': False, 'changes': {}, 'comment': ''}
    changes = {'old': {}, 'new': {}}

    oldval, newval = _ensure_xml_bool(collection_prefs.local_user_accounts, local_users)
    if newval is not None:
        changes['old']['local_users'] = oldval
        changes['new']['local_users'] = newval

    oldval, newval = _ensure_xml_bool(collection_prefs.printers, printers)
    if newval is not None:
        changes['old']['printers'] = oldval
        changes['new']['printers'] = newval

    oldval, newval = _ensure_xml_bool(collection_prefs.home_directory_sizes, home_directory_sizes)
    if newval is not None:
        changes['old']['home_directory_sizes'] = oldval
        changes['new']['home_directory_sizes'] = newval

    oldval, newval = _ensure_xml_bool(collection_prefs.hidden_accounts, hidden_accounts)
    if newval is not None:
        changes['old']['hidden_accounts'] = oldval
        changes['new']['hidden_accounts'] = newval

    if services is not None and (collection_prefs.active_services.text == 'true') != services:
        changes['old']['services'] = collection_prefs.active_services.text == 'true'
        changes['new']['services'] = hidden_accounts
        collection_prefs.active_services.text = str(services)

    if mobile_last_backup is not None and (collection_prefs.mobile_device_app_purchasing_info.text == 'true') != mobile_last_backup:
        changes['old']['mobile_last_backup'] = collection_prefs.mobile_device_app_purchasing_info.text == 'true'
        changes['new']['mobile_last_backup'] = mobile_last_backup
        collection_prefs.mobile_device_app_purchasing_info.text = str(mobile_last_backup)

    if package_receipts is not None and (collection_prefs.package_receipts.text == 'true') != package_receipts:
        changes['old']['package_receipts'] = collection_prefs.package_receipts.text == 'true'
        changes['new']['package_receipts'] = package_receipts
        collection_prefs.package_receipts.text = str(package_receipts)

    if software_updates is not None and (collection_prefs.available_software_updates.text == 'true') != software_updates:
        changes['old']['software_updates'] = collection_prefs.available_software_updates.text == 'true'
        changes['new']['software_updates'] = software_updates
        collection_prefs.available_software_updates.text = str(software_updates)

    if ibeacon_regions is not None and (collection_prefs.computer_location_information.text == 'true') != ibeacon_regions:
        changes['old']['ibeacon_regions'] = collection_prefs.computer_location_information.text == 'true'
        changes['new']['ibeacon_regions'] = ibeacon_regions
        collection_prefs.computer_location_information.text = str(ibeacon_regions)

    if applications is not None and (collection_prefs.include_applications.text == 'true') != applications:
        changes['old']['applications'] = collection_prefs.include_applications.text == 'true'
        changes['new']['applications'] = applications
        collection_prefs.include_applications.text = str(applications)

    if fonts is not None and (collection_prefs.include_fonts.text == 'true') != fonts:
        changes['old']['fonts'] = collection_prefs.include_fonts.text == 'true'
        changes['new']['fonts'] = fonts
        collection_prefs.include_fonts.text = str(fonts)

    if plugins is not None and (collection_prefs.include_plugins.text == 'true') != plugins:
        changes['old']['plugins'] = collection_prefs.include_plugins.text == 'true'
        changes['new']['plugins'] = plugins
        collection_prefs.include_plugins.text = str(plugins)

    if len(changes['new'].keys()) > 0:
        ret['changes'] = changes

        if __opts__['test']:
            ret['result'] = None
            ret['comment'] = '{0} would be modified'.format(name)
        else:
            collection_prefs.save()
            ret['result'] = True
            ret['comment'] = '{0} was updated'.format(name)
    else:
        ret['comment'] = '{0} is already in the desired state'.format(name)
        ret['result'] = True

    return ret




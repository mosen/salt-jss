# Import Python libs
from __future__ import absolute_import, print_function, unicode_literals
import logging
import salt.utils
from xml.etree import ElementTree
from salt.exceptions import (
    CommandExecutionError, MinionError, SaltInvocationError
)
from xml.sax.saxutils import escape

# python-jss
HAS_LIBS = False
try:
    import jss
    from jss import jssobjects
    HAS_LIBS = True
except ImportError:
    pass

logger = logging.getLogger(__name__)
import salt.utils.platform

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


def mod_init(low):
    '''Refresh the policy index here so that it only needs to happen once
    :param low:
    :return:
    '''
    if low['fun'] == 'policy':
        return True

    return False


def _policy_selfservice(policy, self_service=None):
    '''Ensure that self service configuration matches the desired state.

    self_service
        The self-service highstate, which is an object comprised of:
            - enabled (bool): A convenience property for `use_for_self_service` enables or disables self service for the
                policy.

    :returns: Tuple of changed_old, changed_new
    :raises: ValueError on error. Description should be appended to ret['comments']
    '''
    if self_service is None:
        return None, None

    changes_old = {}
    changes_new = {}

    logger.debug('self service:')
    logger.debug(self_service)

    for self_service_item in self_service:
        for k, v in self_service_item.items():
            if k == 'enabled':
                enabled = (policy.self_service.use_for_self_service.text == 'true')
                if v != enabled:
                    changes_old['enabled'] = enabled
                    changes_new['enabled'] = v
                    policy.self_service.use_for_self_service.text = str(v)

    return changes_old, changes_new


def _policy_triggers(policy, triggers=None):
    '''Ensure that policy triggers match the desired state.

    policy
        The Policy JSSObject created or retrieved in jamf.policy

    triggers
        The list of desired triggers.

    :returns: Tuple of changed_old, changed_new
    :raises: ValueError on error. Description should be appended to ret['comments']
    '''
    reserved_triggers = ['startup', 'login', 'logout', 'network_state_changed', 'enrollment_complete', 'checkin']

    if triggers is None:
        return None, None

    old_triggers = set()

    changes_old = []
    changes_new = []

    for rtrig in reserved_triggers:
        try:
            trigger_name = 'trigger_{0}'.format(rtrig)
            logger.debug('Looking for existing trigger: %s', trigger_name)
            if policy.general.findtext(trigger_name) == 'true':
                old_triggers.add(rtrig)
        except ValueError:
            continue

    try:
        if policy.general.findtext('trigger_other'):  # This truthy test covers None and '' empty string
            old_triggers.add(policy.general.findtext('trigger_other'))
    except ValueError:
        pass  # Not an error, just a missing trigger.

    # logger.debug(old_triggers)
    # logger.debug(set(triggers))

    triggers_remove = old_triggers - set(triggers)
    logging.debug('Triggers to remove: %s', triggers_remove)
    triggers_add = set(triggers) - old_triggers
    logging.debug('Triggers to add: %s', triggers_add)

    if len(triggers_add) > 0 or len(triggers_remove) > 0:
        changes_old = list(old_triggers)
        changes_new = triggers

        for remove_trigger in triggers_remove:
            if remove_trigger in reserved_triggers:
                remove_trigger_el = policy.find('general/trigger_{}'.format(remove_trigger))
                if remove_trigger_el is not None and remove_trigger_el.text == 'true':
                    remove_trigger_el.text = 'false'
            else:
                policy.find('general/trigger_other').text = None

        for add_trigger in triggers_add:
            if add_trigger in reserved_triggers:
                add_trigger_el = policy.find('general/trigger_{}'.format(add_trigger))
                if add_trigger_el is not None and add_trigger_el.text == 'false':
                    add_trigger_el.text = 'true'
            else:
                if policy.find('trigger_other') is None:
                    ElementTree.SubElement(policy.general, 'trigger_other')

                policy.find('general/trigger_other').text = add_trigger

    return changes_old, changes_new


def _policy_maintenance(policy, maintenance=None):
    '''Ensure that the `maintenance` section of a policy matches the desired state.

    policy
        The Policy JSSObject created or retrieved in jamf.policy

    maintenance
        The maintenance highstate.

    :returns: Tuple of changed_old, changed_new
    :raises: ValueError on error. Description should be appended to ret['comments']
    '''
    if maintenance is None:
        return None, None

    changes_old = {}
    changes_new = {}

    logger.debug('maintenance:')
    logger.debug(maintenance)

    for maintenance_item in maintenance:
        for k, v in maintenance_item.items():
            if k == 'update_inventory':
                update_inventory = (policy.maintenance.recon.text == 'true')
                if v != update_inventory:
                    changes_old['update_inventory'] = update_inventory
                    changes_new['update_inventory'] = v
                    policy.maintenance.recon.text = str(v)

    return changes_old, changes_new


def _policy_scope(policy, scope=None):
    '''Ensure that the `scope` section of a policy matches the desired state.

    policy
        The Policy JSSObject created or retrieved in jamf.policy

    scope
        The scope highstate.

    :returns: Tuple of changed_old, changed_new
    :raises: ValueError on error. Description should be appended to ret['comments']
    '''
    if scope is None:
        return None, None

    changes_old = {}
    changes_new = {}

    for scope_item in scope:
        for sk, sv in scope_item.items():
            if sk == 'all_computers':
                old_all_computers = policy.find('scope/all_computers')
                if old_all_computers is not None:
                    all_computers = old_all_computers.text == 'true'
                    if sv != all_computers:
                        changes_old['all_computers'] = all_computers
                        old_all_computers.text = str(sv)
                        changes_new['all_computers'] = sv
            elif sk == 'computer_groups':
                j = _get_jss()

                existing_computer_groups = {}
                for existing_computer_group in policy.findall('scope/computer_groups/computer_group'):
                    existing_computer_groups[existing_computer_group.id.text] = existing_computer_group.name.text

                logger.debug('Existing computer groups: %s', existing_computer_groups)

                changes_old['computer_groups'] = existing_computer_groups.values()
                changes_new['computer_groups'] = []
                to_add = set(sv) - set(existing_computer_groups.values())
                to_remove = set(existing_computer_groups.values()) - set(sv)

                for cg in to_add:
                    try:
                        policy.add_object_to_scope(j.ComputerGroup(cg))
                        changes_new['computer_groups'].append(cg)
                    except jss.GetError:
                        raise SaltInvocationError(
                            'Invalid computer group "{}" specified in policy: {}'.format(cg, policy.name))

                for cg in to_remove:
                    cg_match = policy.find('scope/computer_groups/computer_group/[name=\'{}\']'.format(cg))
                    if cg_match is not None:
                        pass
            elif sk == 'exclusions':
                existing_exclusions = {}

    return changes_old, changes_new


def _policy_script(policy, script, priority='Before'):
    '''Ensure that the script exists in the policy with the specified priority.'''
    pass


def _policy_scripts(policy, scripts=None):  # type: (jss.Policy, Optional[List[OrderedDict]]) -> Tuple[Optional[dict], Optional[dict]]
    '''Ensure that the policy scripts actions are in the desired state.

    policy
        The Policy JSSObject created or retrieved in jamf.policy

    scope
        The scope highstate.

    :returns: Tuple of changed_old, changed_new
    :raises: ValueError on error. Description should be appended to ret['comments']
    '''
    if scripts is None:
        return None, None

    changes_old = {}
    changes_new = {}

    existing_scripts = policy.get_scripts()
    logger.debug(existing_scripts)

    for script_priority in scripts:
        for script_priority_name, script_items in script_priority.items():
            if script_priority_name == 'after':
                pass
            elif script_priority_name == 'before':
                pass #policy.add_script()
            else:
                logger.warning('Invalid script priority specified: %s', script_priority_name)

    return None, None


def policy(name,
           frequency,
           enabled=False,
           site=None,
           category=None,
           triggers=None,
           target_drive=None,
           limitations=None,
           scope=None,
           self_service=None,

           # Policy steps
           packages=None,
           software_updates=None,
           scripts=None,
           printers=None,
           disk_encryption=None,
           dock_items=None,
           local_accounts=None,
           management_accounts=None,
           maintenance=None,
           processes=None,
           **kwargs):
    '''Ensure that the given Policy is present.

    The state will not create requisites for dependent objects, you will have to create your own requisites.

    name
        The unique name for the policy. This is also used to determine whether the policy already exists.

    frequency
        Policy frequency, may be one of:
            - Once per computer
            - Once per user per computer
            - Once per user
            - Once every day
            - Once every week
            - Once every month
            - Ongoing

    enabled
        Whether the policy will be enabled or not (Default False)

    site (optional)
        The name of an associated site.

    category (optional)
        The category that the policy will be featured in.

    triggers (optional)
        List of triggers including custom names that will trigger this policy.
        Reserved names are:
            - startup
            - login
            - logout
            - network_state_changed
            - enrollment_complete
            - checkin

    target_drive (optional)
        Drive to run the policy against (defaults to the boot drive '/')

    limitations (optional)
        TBD

    scope (optional)
        TBD

    self_service (optional)
        An object describing Self-Service configuration

    '''
    j = _get_jss()
    ret = {'name': name, 'result': False, 'changes': {}, 'comment': ''}
    changes = {'old': {}, 'new': {}}

    basic_keys = {'enabled', 'frequency', 'location_user_only', 'target_drive', 'offline'}
    frequencies = ['Once per computer', 'Once per user per computer', 'Once per user', 'Once every day',
                   'Once every week', 'Once every month', 'Ongoing']

    if frequency not in frequencies:
        raise SaltInvocationError('Specified frequency "{}" is not a valid policy frequency, one of: {}'.format(
            frequency, ', '.join(frequencies),
        ))

    try:
        pol = j.Policy(name)
    except jss.GetError:
        pol = jss.Policy(j, name)

    # Check Basics
    if enabled != (pol.general.enabled.text == 'true'):
        changes['old']['enabled'] = (pol.general.enabled.text == 'true')
        pol.general.enabled.text = str(enabled)
        changes['new']['enabled'] = enabled

    if frequency != pol.general.frequency.text:
        changes['old']['frequency'] = pol.general.frequency.text
        pol.general.frequency.text = frequency
        changes['new']['frequency'] = frequency

    # Check Site
    # TODO: This does not cover removal of a site? perhaps None should be available
    if site is not None:
        site_el = pol.find('general/site')
        if site_el is None:
            site_el = ElementTree.SubElement(pol.general, 'site')

        oldval, newval = _ensure_xml_str(pol.general, 'name', site)
        if newval is not None:
            changes['old']['site'] = oldval
            changes['new']['site'] = newval

    # Check Category
    if category is not None:
        oldval, newval = _ensure_xml_str(pol.general.category, 'name', category)
        if newval is not None:
            changes['old']['category'] = oldval
            changes['new']['category'] = newval

    # Check Triggers
    try:
        triggers_old, triggers_new = _policy_triggers(pol, triggers)
    except ValueError as e:
        ret['comment'] = 'Failed to update triggers: {0}'.format(e.message)
        ret['result'] = False
        return ret

    if triggers_new is not None and len(triggers_new) > 0:
        changes['old']['triggers'] = triggers_old
        changes['new']['triggers'] = triggers_new

    # Check Scope
    try:
        scope_old, scope_new = _policy_scope(pol, scope)
    except ValueError as e:
        ret['comment'] = 'Failed to update scope: {0}'.format(e.message)
        ret['result'] = False
        return ret

    if scope_new is not None and len(scope_new.keys()) > 0:
        changes['old']['scope'] = scope_old
        changes['new']['scope'] = scope_new

    # Packages
    if packages is not None:
        for item in packages:
            for pk, pv in item.items():
                if pk == 'install':
                    package_tags = pol.package_configuration.packages.findall('package')
                    existing_pkgs_install = set([p.name.text for p in package_tags])
                    pkgs_install_add = set(pv) - existing_pkgs_install
                    pkgs_install_remove = existing_pkgs_install - set(pv)
                    if len(pkgs_install_add) == 0 and len(pkgs_install_remove) == 0:
                        continue

                    changes['old']['packages'] = {'install': list(existing_pkgs_install)}
                    changes['new']['packages'] = {'install': pv}

                    for add_pkg in pkgs_install_add:
                        try:
                            p = j.Package(add_pkg)
                            pol.add_package(p)
                        except jss.GetError:
                            ret['result'] = False
                            ret['comment'] = 'Package named "{0}" does not exist.'.format(add_pkg)
                            return ret

                    for rm_pkg in pkgs_install_remove:
                        try:
                            pol.remove_package(rm_pkg)
                        except ValueError as e:
                            ret['result'] = False
                            ret['comment'] = 'Failed to remove Package named "{0}", Reason: {1}'.format(rm_pkg, e.message)
                            return ret

                elif pk == 'distribution_point':
                    pass

    # Scripts
    # if scripts is not None:
    #     script_tags = pol.scripts.findall('script')
    #     changes['old']['scripts'] = [st.name.text for st in script_tags]
    #
    #     for script in scripts:
    #         script_tag = ElementTree.SubElement(pol.scripts, 'script')
    #         name = ElementTree.SubElement(script_tag, 'name')
    #         name.text = script


    # Scripts
    try:
        scripts_old, scripts_new = _policy_scripts(pol, scripts)
    except ValueError as e:
        ret['comment'] = 'Failed to update scripts: {0}'.format(e.message)
        ret['result'] = False
        return ret

    if scripts_new is not None:
        changes['old']['scripts'] = scripts_old
        changes['new']['scripts'] = scripts_new

    # Maintenance
    try:
        maintenance_old, maintenance_new = _policy_maintenance(pol, maintenance)
    except ValueError as e:
        ret['comment'] = 'Failed to update maintenance tasks: {0}'.format(e.message)
        ret['result'] = False
        return ret

    if maintenance_new is not None:
        changes['old']['maintenance'] = maintenance_old
        changes['new']['maintenance'] = maintenance_new

    # Self Service
    try:
        ss_old, ss_new = _policy_selfservice(pol, self_service)
    except ValueError as e:
        ret['comment'] = 'Failed to update self service: {0}'.format(e.message)
        ret['result'] = False
        return ret

    if ss_new is not None:
        changes['old']['self_service'] = ss_old
        changes['new']['self_service'] = ss_new

    try:
        pol.save()
        ret['result'] = True
        ret['comment'] = 'Policy Updated Successfully'
        ret['changes'] = changes
    except jss.PutError:
        ret['result'] = False
        ret['comment'] = 'Unable to update Policy'

    return ret

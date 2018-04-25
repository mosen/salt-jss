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


def script(name,
           source=None,
           source_hash='',
           source_hash_name=None,
           contents=None,
           template=None,
           context=None,
           defaults=None,
           skip_verify=False,
           **kwargs):
    '''
    Ensure that given script is present.

    name
        Name of the script (must be unique for the entire jss instance).

    category
        Category

    filename
        Filename

    info
        Information

    notes
        Notes

    contents
        Script contents inline

    source
        Managed file source

    **Example:**

    .. code-block:: yaml
        name_or_unique_id:
          jamf.script:
            - name: Script Name
            - category: Category Name
            - filename: filename.sh
            - info: Script information
            - notes: Script notes
            - priority: before | after | reboot
            - parameters:
              - p4
              - p5
              - p6
            - os_requirements: 10.13.x
            - contents: |
                inline content or
            - source: ./path/to/script.sh
            - source_hash: ''
            - source_hash_name:
    '''
    j = _get_jss()
    script_attrs = ['filename', 'info', 'notes', 'os_requirements']  # Treated verbatim
    priorities = {'before': 'Before', 'after': 'After'}

    logger.debug("Searching for existing script with name: {}".format(name))
    retval = {'name': name, 'result': False, 'changes': {}, 'comment': ''}
    changes = {'old': {}, 'new': {}}

    try:
        script = j.Script(name)
        retval['comment'] = 'The script already exists.'
        retval['result'] = True

    except jss.JSSGetError as e:  # TODO: Check 404 only (not 500)
        script = jss.Script(j, name)

    # Basic attributes
    for attr in script_attrs:
        if attr not in kwargs:
            continue  # Don't check for changes on non specified attributes

        logger.debug('Checking element {}'.format(attr))
        attr_el = script.find(attr)

        if attr_el and attr_el.text != kwargs[attr]:
            changes['old'][attr] = script.find(attr).text
            script.find(attr).text = kwargs[attr]
            changes['new'][attr] = kwargs[attr]
        elif attr_el is None:
            attr_el = ElementTree.SubElement(script, attr)
            attr_el.text = kwargs[attr]
            changes['new'][attr] = kwargs[attr]

    # Parameters
    # if len(kwargs.get('parameters', [])) > 0 or script.find('parameter4').text is not None:
    #     for p in range(4, 11):
    #         parameter = 'parameter{}'.format(p)
    #         if parameter not in kwargs:
    #             continue  # Did not specify this parameter so no changes are made.
    #
    #         if script.find(parameter).text != kwargs[parameter]:
    #             script.find(parameter).text = kwargs[parameter]
    #             retval['changes']['new'][parameter] = kwargs[parameter]

    # Contents
    if source and contents is not None:
        raise SaltInvocationError(
            '\'source\' cannot be used in combination with \'contents\', '
        )

    if contents is not None:
        if len(script.find('script_contents').text) > 0:
            changes['old']['contents'] = script.find('script_contents').text

        script.add_script(contents)  # Will be XML encoded
        changes['new']['contents'] = contents
    elif source is not None:
        old_script_contents = script.find('script_contents')
        if old_script_contents is not None:
            changes['old']['contents'] = script.find('script_contents').text

        script_contents = __salt__['file.get_managed'](
            name,
            template,
            source,
            source_hash,
            source_hash_name,
            None,
            None,
            None,
            None,
            __env__,
            context,
            defaults,
            skip_verify
        )
        logger.debug(script_contents)

    if len(changes['old'].keys()) > 0 or len(changes['new'].keys()) > 0:
        retval['changes'] = changes  # Only show changes if there were any

    if __opts__['test']:
        retval['result'] = None
    else:
        script.save()
        retval['result'] = True

    return retval

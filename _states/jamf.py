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

        current_priority = category.find('priority').text
        if current_priority != priority:
            changes['old']['priority'] = current_priority
            category.find('priority').text = str(priority)
            changes['new']['priority'] = str(priority)
            category.save()
            ret['result'] = True

    except jss.JSSGetError as e:
        category = jss.Category(j, name)
        priority_el = ElementTree.SubElement(category, 'priority')
        priority_el.text = str(priority)
        changes['new']['name'] = name
        changes['new']['priority'] = str(priority)
        category.save()
        ret['result'] = True

    ret['changes'] = changes
    return ret


def script(name,
           source=None,
           source_hash='',
           source_hash_name=None,
           contents=None,
           template=None,
           context=None,
           defaults=None,
           skip_verify=True,
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

    template
        If this setting is applied then the named templating engine will be
        used to render the downloaded file. Currently, jinja and mako are
        supported.

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
            - priority: Before | After | reboot
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
    script_attrs = ['filename', 'info', 'notes', 'os_requirements', 'priority']  # Treated verbatim

    logger.debug("Searching for existing script with name: {}".format(name))
    retval = {'name': name, 'result': False, 'changes': {}, 'comment': ''}
    changes = {'old': {}, 'new': {}}

    try:
        script = j.Script(name)  # Script exists, but may be different.
    except jss.JSSGetError as e:
        script = jss.Script(j, name)  # Script does not exist

    # Basic attributes
    for attr in script_attrs:
        if attr not in kwargs:
            continue  # Don't check for changes on non specified attributes

        logger.debug('Checking element {}'.format(attr))
        attr_el = script.find(attr)

        if attr_el is not None and attr_el.text != kwargs[attr]:
            changes['old'][attr] = script.find(attr).text
            script.find(attr).text = kwargs[attr]
            changes['new'][attr] = kwargs[attr]
        elif attr_el is None:
            attr_el = ElementTree.SubElement(script, attr)
            attr_el.text = kwargs[attr]
            changes['new'][attr] = kwargs[attr]

    # Category
    if 'category' in kwargs:
        category_el = script.find('category')
        if category_el is None:
            category_el = ElementTree.SubElement(script, 'category')

        if category_el.text != kwargs['category']:
            changes['old']['category'] = category_el.text
            category_el.text = kwargs['category']
            changes['new']['category'] = kwargs['category']

    # Parameters
    if len(kwargs.get('parameters', [])) > 0:
        for p in range(4, 11):
            parameter = 'parameter{}'.format(p)

            if p - 4 >= len(kwargs['parameters']):
                break  # No more parameters to process

            parameter_el = script.find(parameter)
            if parameter_el is None:
                parameter_el = ElementTree.SubElement(script, parameter)

            if parameter_el.text != kwargs['parameters'][p - 4]:
                parameter_el.text = kwargs['parameters'][p - 4]
                changes['new'][parameter] = kwargs['parameters'][p - 4]

    # Contents
    if source and contents is not None:
        raise SaltInvocationError(
            '\'source\' cannot be used in combination with \'contents\', '
        )

    current_script_contents = script.find('script_contents')

    if contents is not None:
        if current_script_contents is not None:
            changes['old']['contents'] = script.find('script_contents').text

        # script.add_script(contents)  # Will be XML encoded
        escaped_script_contents = escape(contents)
        if current_script_contents is None:
            script_contents_tag = ElementTree.SubElement(
                script, "script_contents")
            script_contents_tag.text = escaped_script_contents

        changes['new']['contents'] = contents
    elif source is not None:
        logger.debug('Retrieving from source {}'.format(source))

        script_tmp_file = salt.utils.files.mkstemp()
        current_script_contents = script.find('script_contents')
        if current_script_contents is not None and current_script_contents.text is not None:
            changes['old']['contents'] = script.find('script_contents').text

            with open(script_tmp_file, 'wb') as fd:
                fd.write(current_script_contents.text)

        sfn, source_sum, comment = __salt__['file.get_managed'](
            name=script_tmp_file,
            template=template,
            source=source,
            source_hash=source_hash,
            source_hash_name=source_hash_name,
            user=None,
            group=None,
            mode=None,
            attrs=[],
            saltenv=__env__,
            context=context,
            defaults=defaults,
            skip_verify=skip_verify,
            **kwargs
        )
        logger.debug('script contents follow')
        logger.debug(sfn)
        logger.debug(source_sum)
        logger.debug(comment)

        # with open(script_tmp_file, 'r') as fd:
        #     lines = fd.readlines()
        #     logger.debug(lines)

        retval['comment'] = comment

    if len(changes['old'].keys()) > 0 or len(changes['new'].keys()) > 0:
        retval['changes'] = changes  # Only show changes if there were any

    if __opts__['test']:
        retval['result'] = None
    else:
        script.save()
        retval['result'] = True

    return retval

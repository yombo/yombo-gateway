"""
Allows templates to be used in various places within Yombo. For example,
they can be used as condition statements for scenes, automation rules, etc.

**Usage**:

.. code-block:: python

   my_template = self._Template.new("It's now {{ now }}.")
   results = my_template.render()

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.18.0

:copyright: Copyright 2018 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
import random
from time import sleep

import jinja2
from jinja2 import contextfilter
from jinja2.sandbox import ImmutableSandboxedEnvironment

# Import twisted libraries
from twisted.internet import threads
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.core.library import YomboLibrary
from yombo.utils import (random_string, is_true_false, forgiving_float, forgiving_round, multiply, logarithm,
                         fail_when_undefined, strptime, is_yes_no, status_to_string, public_to_string, epoch_to_string,
                         excerpt, make_link, format_markdown, display_hide_none)

logger = get_logger("library.templates")
logger_runtime = get_logger("library.templates.runtime")

_WATCHDOG = object()

@contextfilter
def random_choice(context, values):
    """
    Choose a random value from the provided values.
    """
    return random.choice(values)


class Template(YomboLibrary, object):
    """
    Handles compiling templates and rendering them when requested.
    """
    def _init_(self, **kwargs):
        """

        :return:
        """
        pass

    def _load_(self, **kwargs):
        def debug(text):
            logger.info("Template says: {text}", text=text)

        self.environment = TemplateEnvironment()
        self.environment.globals['as_timestamp'] = self._Times.forgiving_as_timestamp
        self.environment.globals['float'] = forgiving_float
        self.environment.globals['log'] = logarithm
        self.environment.globals['now'] = self._Times.now
        self.environment.globals['relative_time'] = self._Times.get_age
        self.environment.globals['sleep'] = sleep
        self.environment.globals['strptime'] = strptime
        self.environment.globals['utcnow'] = self._Times.utcnow

        # self.environment.globals['yombo'] = self
        self.environment.globals['local_gateway'] = self._Gateways.get_local()
        self.environment.globals['amqp'] = self._AMQP
        self.environment.globals['amqpyombo'] = self._AMQPYombo
        self.environment.globals['apiauth'] = self._APIAuth
        self.environment.globals['atoms'] = self._Atoms
        self.environment.globals['automation'] = self._Automation
        self.environment.globals['commands'] = self._Commands
        self.environment.globals['configs'] = self._Configs
        self.environment.globals['crontab'] = self._CronTab
        self.environment.globals['devices'] = self._Devices
        self.environment.globals['devicetypes'] = self._DeviceTypes
        self.environment.globals['gateways'] = self._Gateways
        self.environment.globals['gpg'] = self._GPG
        self.environment.globals['inputtypes'] = self._InputTypes
        self.environment.globals['libraries'] = self._Libraries
        self.environment.globals['localize'] = self._Localize
        self.environment.globals['locations'] = self._Locations
        self.environment.globals['modules'] = self._Modules
        self.environment.globals['mqtt'] = self._MQTT
        self.environment.globals['nodes'] = self._Nodes
        self.environment.globals['notifiticaions'] = self._Notifications
        self.environment.globals['queue'] = self._Queue
        self.environment.globals['scenes'] = self._Scenes
        self.environment.globals['sqldict'] = self._SQLDict
        self.environment.globals['sslcerts'] = self._SSLCerts
        self.environment.globals['states'] = self._States
        self.environment.globals['statistics'] = self._Statistics
        self.environment.globals['tasks'] = self._Tasks
        self.environment.globals['times'] = self._Times
        self.environment.globals['variables'] = self._Variables
        self.environment.globals['validate'] = self._Validate
        # self.environment.globals['voicecmds'] = self._VoiceCmds

        self.environment.filters['debug'] = logger_runtime.debug
        self.environment.filters['info'] = logger_runtime.info
        self.environment.filters['warning'] = logger_runtime.warning
        self.environment.filters['error'] = logger_runtime.error
        self.environment.filters['round'] = forgiving_round
        self.environment.filters['multiply'] = multiply
        self.environment.filters['log'] = logarithm
        self.environment.filters['timestamp_custom'] = self._Times.timestamp_custom
        self.environment.filters['timestamp_local'] = self._Times.timestamp_local
        self.environment.filters['timestamp_utc'] = self._Times.timestamp_utc
        self.environment.filters['is_defined'] = fail_when_undefined
        self.environment.filters['max'] = max
        self.environment.filters['min'] = min
        self.environment.filters['random_choice'] = random_choice
        self.environment.filters['yes_no'] = is_yes_no
        self.environment.filters['excerpt'] = excerpt
        self.environment.filters['make_link'] = make_link
        self.environment.filters['status_to_string'] = status_to_string
        self.environment.filters['public_to_string'] = public_to_string
        self.environment.filters['epoch_to_human'] = epoch_to_string
        self.environment.filters['epoch_to_pretty_date'] = self._Times.get_age # yesterday, 5 minutes ago, etc.
        self.environment.filters['format_markdown'] = format_markdown
        self.environment.filters['hide_none'] = display_hide_none
        self.environment.filters['display_encrypted'] = self._GPG.display_encrypted
        self.environment.filters['display_temperature'] = self._Localize.display_temperature

    # @inlineCallbacks
    # def _started_(self, **kwargs):
    #     print("hello...starting...%s" % self._Times.now())
    #     temp = self.new("hello. {{ now() }} how are you: {{ devices.devices}}")
    #     output = yield temp.render()
    #     print("%s" % output)
    #
    #     temp2 = self.new("hello. {{ mitch }}")
    #     output = yield temp.render({'mitch': 'mitch schwenk', 'joe': 193.2031})
    #     print("%s" % output)

    def new(self, template_content):
        """
        Generate a new complied template object using the provided content.

        :param template_content:
        :return:
        """
        return JinjaTemplate(template_content, self.environment)


class TemplateEnvironment(ImmutableSandboxedEnvironment):
    """
    Yombo Template environment. Used by the template class to create various global
    and filters for the Jinja2 template system.
    """
    def is_safe_callable(self, obj):
        """Test if callback is safe."""
        return super().is_safe_callable(obj)


class JinjaTemplate(object):
    """
    Creates a compiled version of a provided template string. This can be used to render the results when
    needed.
    """

    def __init__(self, template, environment):
        if not isinstance(template, str):
            raise TypeError('Expected template to be a string')

        self.environment = environment
        self.template = template
        self._compiled_code = None
        self._compiled = None

    def ensure_valid(self):
        """
        Check if a template is valid. Raises YomboWarning if it's invalid. Use to validate
        that the current template is valid.
        """
        if self._compiled_code is not None:
            return

        try:
            self._compiled_code = self.environment.compile(self.template)
        except jinja2.exceptions.TemplateSyntaxError as err:
            raise YomboWarning(err)

    def set_template(self, template):
        """
        Change the template contents. Will clear the compiled code cache, and recompile too.

        :param template:
        :return:
        """
        self.template = template
        self._compiled_code = None
        self._compiled = None
        self._ensure_compiled()

    @inlineCallbacks
    def render(self, variables=None):
        """
        Render the already set template. Additional values can be provided as a dictionary.

        This function returns a deferred and must be called with a yield.
        """
        if variables is None:
            variables = {}

        if self._compiled is None:
            self._ensure_compiled()

        results = yield threads.deferToThread(self._render, variables)
        return results

    def _render(self, variables):
        """
        Do the actual rendering. This was split up from the previous method so that it can
        be called in another thread.

        :return:
        """
        try:
            return self._compiled.render(variables).strip()
        except jinja2.TemplateError as err:
            raise Exception(err)

    def _ensure_compiled(self):
        """
        Make sure the template is compiled.
        """
        self.ensure_valid()

        global_vars = self.environment.make_globals({
        })

        self._compiled = jinja2.Template.from_code(self.environment, self._compiled_code, global_vars, None)

        return self._compiled

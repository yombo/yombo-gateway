.. _hooks:

##################
Hooks
##################

One of the most powerful features of the Yombo Gateway is the hook system. This feature allows modules to tightly
integrate into the core of the framework. Durring various events or activites, the Yombo framework can call various
hooks, which are just python functions.  For example, during startup, a module can supply a list of automation rules,
or when an state changes, the module can get notifications.

Modules can also call hooks of their own. For example, an Insteon API module can ask if any modules have
any capabilites of transmitting Insteon commands through a USB/Serial/Network interface. Or, devices can't ask if
any modules want to perform any specific activites before or after a device command executes.

There are two types of hooks:

1) System hooks
2) Module hooks

System Hooks
============

System hooks are called by various Yombo Gateway libraries and have a leading and trailing underscore(_).  For example,
before, the states library call "_states_set_" when a state changes value.


Module Hooks
============

Module hooks are implemented by modules and have a different naming convertion. The standard is:

hook_modulename_some_action

The "hook" part of the name lets developers know to replace this portion with the name of their module (see example
below). "modulename" is the name of the module calling the hook. "some_action" is whatever name the developer chooses
to call the hook.

Lets look at the X10 API module. This module is responsible for accepting X10 commands from the Yombo framework,
processing it, and delivering it to any interface modules that can deliver the X10 command to the power lines.

*Usage**:

First, lets look at the X10 API module that invokes the hook.

.. code-block:: python

   def _load_(self):
        results = global_invoke_all('x10api_interface')  # call all hook_x10api_interface functions of all modules and libraries.
        interfaces = {}
        for component_name, data in results.iteritems():  # component name can be "yombo.modules.x10plm", data is the results that module returned.
            interfaces[data['priority']] = {'name': component_name, 'callback':data['callback']}

        interfaces = OrderedDict(sorted(interfaces.items()))  # lets sort by priority

        self.interface_module = None
        if len(interfaces) == 0:
            logger.warn("X10 API - No X10 Interface module found, disabling X10 support.")
        else:
            key = interfaces.keys()[-1]  # get the key of the highest priority. We don't know the key name.
            self.interface_module = get_component(temp[key])['callback']   # we can only have one interface, highest priority wins!!
        logger.debug("X10 interface: {interface}", interface=self.interface_module)


Now, lets take a look at the Homevision module. The Homevision has relay port, 1-wire interface, etc. It can also
handle X10 commands. Here's how the Homevision module will tell the X10 API module that it can handle X10 commands.

.. code-block:: python

   def homevision_x10_interfaces(self, **kwargs):
       """
       Implements hook_x10_interfaces.
       """
       return {'priority': 0, 'callback': self.x10api_send_command}

   def x10api_send_command(self, **kwargs):
       print "processing x10 command...."

List of system hooks
======================

The list of hooks below are those implemented by the Yombo framework libraries. Additional hooks can be implemented
by third party modules and will not be listed here.

========================================================================================================= =========================================== ============================================================================================================================
Calling Function Location                                                                                 Hook Name                                   Description
========================================================================================================= =========================================== ============================================================================================================================
:py:meth:`Atoms::set() <yombo.lib.atoms.Atoms.set>`                                                       _atoms_set_                                 When a value is about to be assigned to an atom.
:py:meth:`Automation:_module_prestart_() <yombo.lib.automation.Automation._module_prestart_>`             _automation_rules_list_                     Add rules.
:py:meth:`Automation:_module_prestart_() <yombo.lib.automation.Automation._module_prestart_>`             _automation_action_list_                    Add a new platform to 'action' portion of automation system.
:py:meth:`Automation:_module_prestart_() <yombo.lib.automation.Automation._module_prestart_>`             _automation_filter_list_                    Add a new platform to 'filter' portion of automation system.
:py:meth:`Automation:_module_prestart_() <yombo.lib.automation.Automation._module_prestart_>`             _automation_source_list_                    Add a new platform to 'source' portion of automation system.
:py:meth:`Configuration::set <yombo.lib.configuration.Configuration._module_prestart_>`                   _configuration_details_                     Called when a configuration item is changed.
:py:meth:`Configuration::set <yombo.lib.configuration.Configuration.set>`                                 _configuration_set_                         Called when a configuration item is changed.
:py:meth:`Configuration::_module_prestart_ <yombo.lib.configuration.Configuration._module_prestart_>`     _configuration_details_                     Collects detailed information about a configuration option being used.
:py:meth:`Devices::do_command_hook <yombo.lib.devices.Devices.do_command_hook>`                           _device_command_                            Sends request for any responsible modules to perform the command for a given device.
:py:meth:`Devices::do_command_hook <yombo.lib.devices.Devices.load_device>`                               _device_loaded_                             Called when a new device is added.
:py:meth:`Modules::load_modules <yombo.lib.modules.Modules.load_modules>`                                 _module_devicetypes_                        Calls this funciton just before _init_ happens.
:py:meth:`Modules::load_modules <yombo.lib.modules.Modules.load_modules>`                                 _module_init_                               Only calls to libraries: Called before modules called with _init_.
:py:meth:`Modules::load_modules <yombo.lib.modules.Modules.load_modules>`                                 _module_preload_                            Only calls to libraries: Called before modules called with _preload_.
:py:meth:`Modules::load_modules <yombo.lib.modules.Modules.load_modules>`                                 _module_load_                               Only calls to libraries: Called before modules called with _load_.
:py:meth:`Modules::load_modules <yombo.lib.modules.Modules.load_modules>`                                 _module_prestart_                           Only calls to libraries: Called before modules called with _prestart_.
:py:meth:`Modules::load_modules <yombo.lib.modules.Modules.load_modules>`                                 _module_start_                              Only calls to libraries: Called before modules called with _start_.
:py:meth:`Modules::load_modules <yombo.lib.modules.Modules.load_modules>`                                 _module_started_                            Only calls to libraries: Called before modules called with _started_.
:py:meth:`Modules::load_modules <yombo.lib.modules.Modules.load_modules>`                                 _preload_                                   Only called to modules: Called before _load_ function of a module is called.
:py:meth:`Modules::load_modules <yombo.lib.modules.Modules.load_modules>`                                 _load_                                      Only called to modules: Called during the load phase of a module.
:py:meth:`Modules::load_modules <yombo.lib.modules.Modules.load_modules>`                                 _prestart_                                  Only called to modules: Called before _prestart_ function of a module is called.
:py:meth:`Modules::load_modules <yombo.lib.modules.Modules.load_modules>`                                 _start_                                     Only called to modules: Called during the start phase of the module.
:py:meth:`Modules::load_modules <yombo.lib.modules.Modules.load_modules>`                                 _started_                                   Only called to modules: Called after _start_.
:py:meth:`Modules::unload_modules <yombo.lib.modules.Modules.load_modules>`                               _module_stop_                               Only calls to libraries: Called before modules called with _stop_.
:py:meth:`Modules::unload_modules <yombo.lib.modules.Modules.load_modules>`                               _module_unload_                             Only calls to libraries: Called before modules called with _unload_.
:py:meth:`Modules::unload_modules <yombo.lib.modules.Modules.load_modules>`                               _stop_                                      Only called to modules: Calls as part of _stop_ sequence.
:py:meth:`Modules::unload_modules <yombo.lib.modules.Modules.load_modules>`                               _unload_                                    Only called to modules: Calls as part of _unload_ sequence.
:py:meth:`States::unload_modules <yombo.lib.states.States.set>`                                           _states_set_                                Called when a state value is about to change. Module can raise "YomboHookStopProcessing" exception to halt,
:py:meth:`Times::send_event_hook <yombo.lib.times.Times.send_event_hook>`                                 _time_event_                                When when a times event happens. Sunset, sunrise, twilight, dark, light. Etc.
:py:meth:`MQTT::_module_prestart_ <yombo.lib.mqtt.MQTT._module_prestart_>`                                webinterface_add_routes                     Added MQTT features to web interface library.
:py:meth:`VoiceCmds::_module_prestart_ <yombo.lib.voicecmds.VoiceCmds._module_prestart_>`                 _voicecmds_add_                             Called to add additional voice commands.
========================================================================================================= =========================================== ============================================================================================================================

List of system hooks implemented by modules
===========================================

These are hooks reserved for modules to use as needed.


============================================ ============================================================================================================================
 Hook Name                                   Description
============================================ ============================================================================================================================
_do_command_status_                          In response to _device_command_. Used to sends status of device: done, working, error

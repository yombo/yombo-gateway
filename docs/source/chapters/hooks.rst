.. _hooks:

##################
Hooks
##################

For details on implementing new module hooks, or how to access the system hooks, review the module development
documentation on `hooks <https://yombo.net/docs/modules/hooks/>`_.


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
:py:meth:`Configuration::set <yombo.lib.configuration.Configuration.set>`                                 _configuration_set_                         Called when a configuration item is changed.
:py:meth:`Configuration::_module_prestart_ <yombo.lib.configuration.Configuration._module_prestart_>`     _configuration_details_                     Collects detailed information about a configuration option being used.
:py:meth:`Devices::do_command_hook <yombo.lib.devices.Devices.do_command_hook>`                           _device_command_                            Sends request for any responsible modules to perform the command for a given device.
:py:meth:`Devices::load_device <yombo.lib.devices.Devices.load_device>`                                   _device_loaded_                             Called when a new device is added.
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


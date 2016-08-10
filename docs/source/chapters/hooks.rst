.. _hooks:

##################
Hooks
##################

Yombo's module system also implements a concept of "hooks". A hook is a python function that is can be called from
other libraries or modules. Hooks allow modules to interact with the framework core. It also allows modules and
libraries to capture or respond to various events. For example, before a device recieves a command, another module
can send an alert ahead of time.

A hook is a specially named function, such as "Example_do_something()", where "Example" is the name of the module and
"do_something" is the name of the hook. Within any documentation, the string "hook" is a placeholder for the module
name. In the above example, we would call this "hook_do_something".

To extend Yombo, a module simply needs to implement a hook. At certain events, libraries or modules can invoke all
hooks with a given name.

The list of hooks below are those implemented by the Yombo framework libraries. Additional hooks can be implemented
by third party modules and will not be listed here.

Any hooks ending in "_alter" continue pass in various data as appropiate; however, any data returned will modifiy the
data sent in. This allows any modules to interact with framework at a deeper level.

For performance reasons, a cache is generated of all available hooks and is cleared on restart.

.. note::

  Special hooks, those ending and begining with a single underscore (_) do not have the module name in front of them.

========================================================================================================= =========================================== ==========================================================================================
Calling Function Location                                                                                 Hook Name                                   Description
========================================================================================================= =========================================== ==========================================================================================
:py:meth:`Atoms::set() <yombo.lib.atoms.Atoms.set>`                                                       hook_atoms_set                              When a value is about to be assigned to an atom.
:py:meth:`Automation:_module_prestart_() <yombo.lib.automation.Automation._module_prestart_>`             hook_automation_rules_list                  Add rules.
:py:meth:`Automation:_module_prestart_() <yombo.lib.automation.Automation._module_prestart_>`             hook_automation_action_list                 Add a new platform to 'action' portion of automation system.
:py:meth:`Automation:_module_prestart_() <yombo.lib.automation.Automation._module_prestart_>`             hook_automation_filter_list                 Add a new platform to 'filter' portion of automation system.
:py:meth:`Automation:_module_prestart_() <yombo.lib.automation.Automation._module_prestart_>`             hook_automation_source_list                 Add a new platform to 'source' portion of automation system.
:py:meth:`Configuration::set <yombo.lib.configuration.Configuration.set>`                                 configuration_set                           Called when a configuration item is changed.
:py:meth:`Configuration::_module_prestart_ <yombo.lib.configuration.Configuration._module_prestart_>`     hook_configuration_details                  Collects detailed information about a configuration option being used.
:py:meth:`Messages::_module_prestart_()<yombo.lib.automation.Automation._module_prestart_>`               hook_message_subscriptions                  Subscribe a module to a message type.
:py:meth:`Messages::_module_prestart_()<yombo.lib.automation.Automation._module_prestart_>`               hook_message_subscriptions                  Add subscriptions for messages.
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
:py:meth:`MQTT::_module_prestart_ <yombo.lib.mqtt.MQTT._module_prestart_>`                                webinterface_add_routes                     Added MQTT features to web interface library.
:py:meth:`VoiceCmds::_module_prestart_ <yombo.lib.voicecmds.VoiceCmds._module_prestart_>`                 hook_voice_cmds_add                         Called to add additional voice commands.
========================================================================================================= =========================================== ==========================================================================================

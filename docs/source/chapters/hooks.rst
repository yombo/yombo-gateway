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

========================================================================================================= =========================================== =========================================================================
Calling Function Location                                                                                 Hook Name                                   Description
========================================================================================================= =========================================== =========================================================================
:py:meth:`Atoms::set() <yombo.lib.atoms.Atoms.set>`                                                       hook_atoms_set                              When a value is about to be assigned to an atom.
:py:meth:`Automation:module_prestart() <yombo.lib.automation.Automation._module_prestart_>`               automation_rules_list                       Add rules.
:py:meth:`Automation:module_prestart() <yombo.lib.automation.Automation._module_prestart_>`               automation_action_list                      Add a new platform to 'action' portion of automation system.
:py:meth:`Automation:module_prestart() <yombo.lib.automation.Automation._module_prestart_>`               automation_filter_list                      Add a new platform to 'filter' portion of automation system.
:py:meth:`Automation:module_prestart() <yombo.lib.automation.Automation._module_prestart_>`               automation_source_list                      Add a new platform to 'source' portion of automation system.
:py:meth:`Automation:module_prestart() <yombo.lib.automation.Automation._module_prestart_>`               automation_source_list                      Add platforms to the action automation system.
:py:meth:`Messages::module_prestart()<yombo.lib.automation.Automation._module_prestart_>`                 message_subscriptions                       Subscribe a module to a message type.
:py:meth:`Messages::module_prestart()<yombo.lib.automation.Automation._module_prestart_>`                 message_subscriptions                       Add subscriptions for messages.
:py:meth:`Modules::_module_init_ <yombo.lib.modules.Modules.load_modules_>`                               _module_init_                               Only calls to libraries: called before modules are imported.
:py:meth:`Modules::_module_preload_ <yombo.lib.modules.Modules.load_modules_>`                            _module_init_                               Only calls to libraries: called before modules are imported.
:py:meth:`Modules::_preload_ <yombo.lib.modules.Modules.load_modules_>`                                   _module_init_                               Called before _load_ function of a module is called.
:py:meth:`Modules::_load_ <yombo.lib.modules.Modules.load_modules_>`                                      _module_init_                               Called during the load phase of a module.
:py:meth:`Modules::_prestart_ <yombo.lib.modules.Modules.load_modules_>`                                  _module_init_                               Called before _prestart_ function of a module is called.
:py:meth:`Modules::_start_ <yombo.lib.modules.Modules.load_modules_>`                                     _module_init_                               Called during the start phase of the module.
:py:meth:`Modules::_started_ <yombo.lib.modules.Modules.load_modules_>`                                   _module_init_                               Called after _start_.
:py:meth:`VoiceCmds::_module_prestart_ <yombo.lib.modules.Modules.load_modules_>`                         voice_cmds_add                              Called to add additional voice commands.
========================================================================================================= =========================================== =========================================================================

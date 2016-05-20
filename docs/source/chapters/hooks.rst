.. _hooks:

##################
Hooks
##################

Hooks allow modules to interact with the framework core.

Yombo's module system also implements a concept of "hooks". A hook is a python function that is can be called from
other libraries or modules.

A hook is a specially named function, such as "example_bar()", where "example" is the name of the module and "bar" is
the name of the hook. Within any documentation, the string "hook" is a placeholder for the module name.

To extend Yombo, a module simply needs to implement a hook. When Yombo wishes to allow intervention from modules, it
determines which modules implement a hook and calls them

The available hooks defined as a core feature are explained here in the Hooks section of the developer documentation.

Any hooks ending in "_alter" will will send in a dictionary of items that is about to be processed. This allows a
module to make various modifications on that data. No data needs to be returns as the data will be updated due being
passed in by reference.

=========================== ================================================================================================== ========================== ==============================================================
Source                      Hook Name                                                                                          When Called                Description
=========================== ================================================================================================== ========================== ==============================================================
Automation                  :py:meth:`automation_action_list <yombo.lib.automation.Automation._module_prestart_>`              module_prestart            Add actions available for rules
Automation                  :py:meth:`automation_filter_list <yombo.lib.automation.Automation._module_prestart_>`              module_prestart            Add filter processors for triggers and conditions
Automation                  :py:meth:`automation_rules_list <yombo.lib.automation.Automation._module_prestart_>`               module_prestart            Add rules
Automation                  :py:meth:`automation_source_list <yombo.lib.automation.Automation._module_prestart_>`              module_prestart            Add value sources for triggers and conditions
Messages                    :py:meth:`message_subscriptions <yombo.lib.automation.Automation._module_prestart_>`               module_prestart            Add subscriptions for messages.
VoiceCmds                   :py:meth:`voicecmds_add <yombo.lib.automation.Automation._module_prestart_>`                       module_prestart            Add add voice commands
=========================== ================================================================================================== ========================== ==============================================================

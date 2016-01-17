.. _hooks:

##################
Hooks
##################

Yombo's module system also implements a concept of "hooks". A hook is a
python function that is can be called from other libraries or modules.

Hooks are typically used for two primary reasons:
1. Allows a module or library to modify something before an action takes place
2. By API type modules and libraries that extend the funcationality of
  the gateway.

A hook is a specially named function, sus as "example_bar()", where
"example" is the name of the module and "bar" is name the hook.
Within any documentation, the string "hook" is a placeholder for the module name.

For example, the messages library will call hook_subscriptions to get a list
of messages subscriptions. The voicecmds library will call
hook_voicecmds. The automation module will call several hooks to look for
rules, source and filter processors, action handlers, etc.

Any hooks ending in "_alter" will will send in a dictionary of items that
allows a module to manipulate any values. For example, the messages library
will call hook_subscriptions_alter after hook_subscriptions. This would allow
a module to alter any subscriptions as needed.

=========================== ========================================================================= ========================== ==============================================================
Source                      Hook Name                                                                 When Called                Description
=========================== ========================================================================= ========================================== ==============================================================
Automation                  :meth:`automation_source_list <automation_source_list>`                   module_prestart            Add value sources for triggers and conditions
Automation                  automation_filter_list                                                    module_prestart            Add filter processors for triggers and conditions
Automation                  automation_action_list                                                    module_prestart            Add actions available for rules
Messages                    message_subscriptions                                                     module_prestart            Add subscriptions for messages.
VoiceCmds                   voicecmds_add                                                             module_prestart            Add add voice commands

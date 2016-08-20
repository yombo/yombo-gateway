.. gateway-changelog:

####################################
Changelog Highlights
####################################

Below is a brief history of changes to the Yombo Gateway framework.
August 14, 2016 - 0.12.0
==============================

New Features
---------------

* Split up AMQPYombo module. Now it's AMQPYombo and AMQP. This allows modules to connection to various AMQP servers and
  to subscribe to queues or publish messages to exchanges.
* Gateway can now start if offline. When connects, it will retrieve and send any updates as needed.

Enhancements
---------------

* Started implementing live-updates for devices and commands. However, at this time, still need a reboot
  for everything to take affect. The goal is to allow the majority of these changes to occur without requiring reboot.
* Started making steps to allowing the gateway to start even when offline.
* WebInterface library now uses database to store it's session state information, versus sqldict's.

Misc
-------

* Device types for a module are no longer registered with Yombo, instead, the module implements a hook so the gateway
  can get this information directly from the module.

August 5, 2016 - 0.11.0
==============================

New Features
---------------

* Gateway run modes - 'run', 'config'. Found in states - operation_mode (available after load phase of libraries.
  Otherwise can be found in load.operation_mode. This is handled by the startup library.
* Web interface - Allows user to configure their gateway 100% from the browser. No more command prompts, ini files, etc.
* Hashid - Allow to easily convert ints to short strings:  123 = yX  Can be called through the utils functions.
* YomboAPI - Created bare framework for making API requests to api.yombo.net
* Automation system - Create simple rules to be run. Create an automation.txt file. See automation.txt-sample
* MQTT - Allow connecting to MQTT servers, subscribe, and publish.

Enhancements
---------------

* Configurations now track changes better and has meta data. Added hook 'hook_configuration_details' to collect
  additional details.

Notes
-------

* GPG Progressing - made large strides on getting encryption working again. Needs some TLC.

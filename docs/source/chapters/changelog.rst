.. configuring-the-gateway:

####################################
Changelog Highlights
####################################

Below is a brief history of changes to the Yombo Gateway framework.

July 27, 2016 - 0.11.0
======================

New Features
------------

* Gateway run modes - 'run', 'config'. Found in states - operation_mode (available after load phase of libraries.
  Otherwise can be found in load.operation_mode. This is handled by the startup library.
* Web interface - Allows user to configure their gateway 100% from the browser. No more command prompts, ini files, etc.
* Hashid - Allow to easily convert ints to short strings:  123 = yX  Can be called through the utils functions.
* YomboAPI - Created bare framework for making API requests to api.yombo.net
* Automation system - Create simple rules to be run. Create an automation.txt file. See automation.txt-sample

Enhancements
------------

* Configurations now track changes better and has meta data. Added hook 'hook_configuration_details' to collect
  additional details.

Misc
----

* GPG Progressing - made large strides on getting encryption working again. Needs some TLC.

Fixes
-----

* Toooo many to list.
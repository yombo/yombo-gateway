Module Unit Testing
===================
This goal of this module is to perform unit testing on various modules. To include
unit tests in your module...

The goal of this module is to test all frame libraries and core functions.

As of Aug 3, 2013, it dosn't do much. But that's the goal.

ToDo List
===========

List of unit tests to create...

* Test messages - Commands
** Sending a basic message.
** Sending delayed message using "delay"
** Sending delayed message using "notBefore"
** Sending delayed message using maxDelay
** That it can be canceled, and it does get canceled

* Test messages - Status
** Test fake event broadcasts - "isNowTested"

* Devices
** We can control an unlocked (nopin) device and status message gets generated
** We can control a locked device, gets refused.
** We can control a locked device with pin, ges through
** We can control a locked device, using pin bypass.

License
=======

Same license as Yombo Gateway.

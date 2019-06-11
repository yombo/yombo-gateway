import atoms from '@/services/gwapiv1/atoms';
import automation_rules from '@/services/gwapiv1/automation_rules';
import configurations from '@/services/gwapiv1/configurations';
import debug from '@/services/gwapiv1/debug';
import device_commands from '@/services/gwapiv1/device_commands';
import scenes from '@/services/gwapiv1/scenes';
import states from '@/services/gwapiv1/states';

import user from '@/services/gwapiv1/user';
import system from '@/services/gwapiv1/system';

export default {
    atoms() {
      return atoms;
    },
    automation_rules() {
      return automation_rules;
    },
    configurations() {
      return configurations;
    },
    debug() {
      return debug;
    },
    device_commands() {
      return device_commands;
    },
    states() {
      return states;
    },
    scenes() {
      return scenes;
    },
    user () {
      return user;
    },
    system () {
      return system;
    },
}

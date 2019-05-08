import atoms from '@/services/gwapiv1/atoms';
import automation_rules from '@/services/gwapiv1/automation_rules';
import configurations from '@/services/gwapiv1/configurations';
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
    states() {
      return states;
    },

    user () {
      return user;
    },
    system () {
      return system;
    },
}

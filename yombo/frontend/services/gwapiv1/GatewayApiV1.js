import atoms from '@/services/gwapiv1/atoms';
import automation_rules from '@/services/gwapiv1/automation_rules';
import yombo_ini from '@/services/gwapiv1/yombo_ini';
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
    yombo_ini() {
      return yombo_ini;
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

import atoms from '@/services/gwapiv1/atoms';
import states from '@/services/gwapiv1/states';

import user from '@/services/gwapiv1/user';
import system from '@/services/gwapiv1/system';

export default {
    atoms() {
      return atoms;
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

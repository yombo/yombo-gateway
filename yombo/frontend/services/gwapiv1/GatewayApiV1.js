import user from '@/services/gwapiv1/user';
import system from '@/services/gwapiv1/system';

export default {
    user () {
      return user;
    },
    system () {
      return system;
    },
}

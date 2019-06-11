import gwapiv1 from '@/services/gwapiv1'

export default {
    debug(debug_type) {
      let uri = "debug?debug_type=" + debug_type;
      return gwapiv1().get(uri);
    },
    // devices() {
    //   return gwapiv1().get('devices');
    // },
}

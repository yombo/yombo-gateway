import gwapiv1 from '@/services/gwapiv1'

export default {
    info() {
        return gwapiv1().get('system/info');
    },
}

import gwapiv1 from '@/services/gwapiv1'

export default {
    all() {
        return gwapiv1().get('configurations');
    },
}

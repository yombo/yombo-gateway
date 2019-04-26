import gwapiv1 from '@/services/gwapiv1'

export default {
    access_token() {
        return gwapiv1().get('user/access_token');
    },
}

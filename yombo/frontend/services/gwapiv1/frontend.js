import gwapiv1 from '@/services/gwapiv1'

export default {
    navbar_items() {
        return gwapiv1().get('frontend/navbar_items');
    },
}

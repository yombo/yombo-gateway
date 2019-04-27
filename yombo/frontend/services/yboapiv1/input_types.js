import yboapiv1 from '@/services/yboapiv1'

export default {
    all () {
        return yboapiv1().get('/input_types')
    },
    allGW () {
        return yboapiv1().get('/gateways/'+ window.$nuxt.$gwenv.gateway_id +'/relationships/input_types')
    },
    find(id) {
        return yboapiv1().get('/input_types/' + id);
    },
}

import yboapiv1 from '@/services/yboapiv1'

export default {
    all () {
        return yboapiv1().get('/modules')
    },
    allGW () {
        return yboapiv1().get('/gateways/'+ window.$nuxt.$gwenv.gateway_id +'/relationships/modules')
    },
    fetchOne(id) {
        return yboapiv1().get('/modules/' + id);
    },
}

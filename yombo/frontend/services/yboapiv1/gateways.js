import yboapiv1 from '@/services/yboapiv1'

export default {
    all () {
        return yboapiv1().get('/gateways')
    },
    allGW () {
        return yboapiv1().get('/gateways/'+ window.$nuxt.$gwenv.gateway_id +'/relationships/gateways')
    },
    fetchOne(id) {
        return yboapiv1().get('/gateways/' + gatewayId);
    },
}

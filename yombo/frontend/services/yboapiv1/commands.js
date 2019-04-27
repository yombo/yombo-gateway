import yboapiv1 from '@/services/yboapiv1'

export default {
    all () {
        return yboapiv1().get('/commands')
    },
    allGW () {
        return yboapiv1().get('/gateways/'+ window.$nuxt.$gwenv.gateway_id +'/relationships/commands')
    },
    find(id) {
        return yboapiv1().get('/commands/' + id);
    },
}

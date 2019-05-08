import yboapiv1 from '@/services/yboapiv1'

export default {
    all () {
        return yboapiv1().get('/device_types')
    },
    allGW () {
        return yboapiv1().get('/gateways/'+ window.$nuxt.$gwenv.gateway_id +'/relationships/device_types')
    },
    fetchOne(id) {
        return yboapiv1().get('/device_types/' + id);
    },
}

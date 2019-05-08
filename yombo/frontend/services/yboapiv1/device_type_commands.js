import yboapiv1 from '@/services/yboapiv1'

export default {
    all () {
        return yboapiv1().get('/device_type_commands')
    },
    allGW () {
        return yboapiv1().get('/gateways/'+ window.$nuxt.$gwenv.gateway_id +'/relationships/device_type_commands')
    },
    fetchOne(id) {
        return yboapiv1().get('/device_type_commands/' + id);
    },
}

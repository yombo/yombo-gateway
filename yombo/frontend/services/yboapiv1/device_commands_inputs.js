import yboapiv1 from '@/services/yboapiv1'

export default {
    all () {
        return yboapiv1().get('/device_command_inputs')
    },
    allGW () {
        return yboapiv1().get('/gateways/'+ window.$nuxt.$gwenv.gateway_id +'/relationships/device_command_inputs')
    },
    find(id) {
        return yboapiv1().get('/device_command_inputs/' + id);
    },
}

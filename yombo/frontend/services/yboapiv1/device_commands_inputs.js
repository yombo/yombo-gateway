export default {
    all () {
        return window.$nuxt.$yboapiv1axios.get('/device_command_inputs')
    },
    allGW () {
        return window.$nuxt.$yboapiv1axios.get('/gateways/'+ window.$nuxt.$gwenv.gateway_id +'/relationships/device_command_inputs')
    },
    fetchOne(id) {
        return window.$nuxt.$yboapiv1axios.get('/device_command_inputs/' + id);
    },
}

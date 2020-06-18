export default {
    all () {
        return window.$nuxt.$yboapiv1axios.get('/device_type_commands')
    },
    allGW () {
        return window.$nuxt.$yboapiv1axios.get('/gateways/'+ window.$nuxt.$gwenv.gateway_id +'/relationships/device_type_commands')
    },
    fetchOne(id) {
        return window.$nuxt.$yboapiv1axios.get('/device_type_commands/' + id);
    },
}

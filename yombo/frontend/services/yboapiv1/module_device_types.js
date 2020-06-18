export default {
    all () {
        return window.$nuxt.$yboapiv1axios.get('/module_device_types')
    },
    allGW () {
        return window.$nuxt.$yboapiv1axios.get('/gateways/'+ window.$nuxt.$gwenv.gateway_id +'/relationships/module_device_types')
    },
    fetchOne(id) {
        return window.$nuxt.$yboapiv1axios.get('/module_device_types/' + id);
    },
}

export default {
    all() {
        return window.$nuxt.$yboapiv1axios.get('/device_types')
    },
    allGW() {
        return window.$nuxt.$yboapiv1axios.get('/gateways/'+ window.$nuxt.$gwenv.gateway_id +'/relationships/device_types')
    },
    fetchOne(id) {
        return window.$nuxt.$yboapiv1axios.get('/device_types/' + id);
    },
}

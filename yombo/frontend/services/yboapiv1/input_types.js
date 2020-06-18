export default {
    all () {
        return window.$nuxt.$yboapiv1axios.get('/input_types')
    },
    allGW () {
        return window.$nuxt.$yboapiv1axios.get('/gateways/'+ window.$nuxt.$gwenv.gateway_id +'/relationships/input_types')
    },
    fetchOne(id) {
        return window.$nuxt.$yboapiv1axios.get('/input_types/' + id);
    },
}

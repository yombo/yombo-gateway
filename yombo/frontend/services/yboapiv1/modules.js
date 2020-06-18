export default {
    all () {
        return window.$nuxt.$yboapiv1axios.get('/modules')
    },
    allGW () {
        return window.$nuxt.$yboapiv1axios.get('/gateways/'+ window.$nuxt.$gwenv.gateway_id +'/relationships/modules')
    },
    fetchOne(id) {
        return window.$nuxt.$yboapiv1axios.get('/modules/' + id);
    },
}

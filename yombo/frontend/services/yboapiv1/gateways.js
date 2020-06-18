export default {
    all () {
        return window.$nuxt.$yboapiv1axios.get('/gateways')
    },
    allGW () {
        return window.$nuxt.$yboapiv1axios.get('/gateways/'+ window.$nuxt.$gwenv.gateway_id +'/relationships/gateways')
    },
    fetchOne(id) {
        return window.$nuxt.$yboapiv1axios.get('/gateways/' + gatewayId);
    },
}

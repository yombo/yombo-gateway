export default {
    all () {
        return window.$nuxt.$yboapiv1axios.get('/commands')
    },
    allGW () {
        return window.$nuxt.$yboapiv1axios.get('/gateways/'+ window.$nuxt.$gwenv.gateway_id +'/relationships/commands')
    },
    fetchOne(id) {
        return window.$nuxt.$yboapiv1axios.get('/commands/' + id);
    },
}

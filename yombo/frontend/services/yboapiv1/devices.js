export default {
    all () {
        return window.$nuxt.$yboapiv1axios.get('/devices?include=variables')
    },
    allGW () {
        return window.$nuxt.$yboapiv1axios.get('/gateways/'+ window.$nuxt.$gwenv.gateway_id +'/relationships/devices?include=variables')
    },
    fetchOne(id) {
        // console.log("devices find: " + id);
        return window.$nuxt.$yboapiv1axios.get('/devices/' + id + '?include=variables');
    },
    delete(id, data) {
        // console.log("devices delete: " + id);
        // console.log(data);
        return window.$nuxt.$yboapiv1axios.delete('/devices/' + id);
    },
    patch(id, data) {
        // console.log("devices patch: " + id);
        // console.log(data);
        return window.$nuxt.$yboapiv1axios.patch('/devices/' + id, data);
    },
}

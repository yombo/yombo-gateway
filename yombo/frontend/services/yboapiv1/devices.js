import yboapiv1 from '@/services/yboapiv1'

export default {
    all () {
        return yboapiv1().get('/devices')
    },
    allGW () {
        return yboapiv1().get('/gateways/'+ window.$nuxt.$gwenv.gateway_id +'/relationships/devices')
    },
    find(id) {
        // console.log("devices find: " + id);
        return yboapiv1().get('/devices/' + id);
    },
}

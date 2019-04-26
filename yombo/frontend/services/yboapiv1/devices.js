import yboapiv1 from '@/services/yboapiv1'

export default {
    all () {
        return yboapiv1().get('/gateways/'+ window.$nuxt.$gwenv.gateway_id +'/relationships/devices')
    },

    find(deviceId) {
        console.log("devices find: " + deviceId);
        return yboapiv1().get('devices/' + deviceId);
    },
}

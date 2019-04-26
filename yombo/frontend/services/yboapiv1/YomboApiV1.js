import devices from '@/services/yboapiv1/devices';


export default {
    devices () {
        return devices
    },
    // LocationsGet () {
    //     return yboapiv1().get('Locations')
    // },
    //
    // // These are gateway specific.
    // CommandsGet ({
    //       request_type2 = 'gateway',
    //       }={}) {
    //
    //     // console.log("Named params...." + request_type2);
    //     if (request_type2 == "gateway") {
    //       return yboapiv1().get('/gateways/'+ window.$nuxt.$gwenv.gateway_id +'/relationships/commands')
    //     } else {
    //       return yboapiv1().get('/commands')
    //     }
    // },
    //
    // DevicesGetOne (id) {
    //     return yboapiv1().get('devices/'+id)
    // },
    // DevicesGet ({
    //       request_type2 = 'gateway',
    //       }={}) {
    //
    //     // console.log("Named params...." + request_type2);
    //     if (request_type2 == "gateway") {
    //       return yboapiv1().get('/gateways/'+ window.$nuxt.$gwenv.gateway_id +'/relationships/devices')
    //     } else {
    //       return yboapiv1().get('/devices')
    //     }
    // },
    //
    // DeviceTypesGet () {
    //     return yboapiv1().get('device_types')
    // },
    // DeviceTypeCommandsGet () {
    //     return yboapiv1().get('gateways')
    // },
}

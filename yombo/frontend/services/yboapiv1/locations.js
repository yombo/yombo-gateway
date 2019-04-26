import yboapiv1 from '@/services/yboapiv1'

export default {
    all () {
        return yboapiv1().get('/locations')
    },
    find(locationId) {
        console.log("locations find: " + locationId);
        return yboapiv1().get('locations/' + locationId);
    },
}

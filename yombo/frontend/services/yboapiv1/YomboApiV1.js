import categories from '@/services/yboapiv1/categories';
import devices from '@/services/yboapiv1/devices';
import locations from '@/services/yboapiv1/locations';


export default {
    categories () {
        return categories
    },
    devices () {
        return devices
    },
    locations () {
        return locations
    },
}

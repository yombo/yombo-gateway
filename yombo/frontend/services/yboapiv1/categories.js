import yboapiv1 from '@/services/yboapiv1'

export default {
    all () {
        return yboapiv1().get('/categories')
    },
    find(locationId) {
        console.log("categories find: " + locationId);
        return yboapiv1().get('categories/' + locationId);
    },
}

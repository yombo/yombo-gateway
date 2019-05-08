import yboapiv1 from '@/services/yboapiv1'

export default {
    all () {
        return yboapiv1().get('/locations')
    },
    fetchOne(id) {
        return yboapiv1().get('/locations/' + id);
    },
}

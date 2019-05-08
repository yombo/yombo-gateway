import yboapiv1 from '@/services/yboapiv1'

export default {
    all () {
        return yboapiv1().get('/categories')
    },
    fetchOne(id) {
        return yboapiv1().get('/categories/' + id);
    },
}

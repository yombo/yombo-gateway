import yboapiv1 from '@/services/yboapiv1'

export default {
    all () {
        return yboapiv1().get('/categories')
    },
    find(id) {
        return yboapiv1().get('/categories/' + id);
    },
}

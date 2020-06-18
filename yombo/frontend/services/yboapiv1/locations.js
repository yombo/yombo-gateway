export default {
    all () {
        return window.$nuxt.$yboapiv1axios.get('/locations')
    },
    fetchOne(id) {
        return window.$nuxt.$yboapiv1axios.get('/locations/' + id);
    },
}

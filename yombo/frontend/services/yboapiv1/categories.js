export default {
    all () {
        return window.$nuxt.$yboapiv1axios.get('/categories')
    },
    fetchOne(id) {
        return window.$nuxt.$yboapiv1axios.get('/categories/' + id);
    },
}

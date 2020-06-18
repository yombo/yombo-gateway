export default {
    all() {
        return window.$nuxt.$gwapiv1axios.get('lib/authkeys');
    },
    fetchOne(id) {
        return window.$nuxt.$gwapiv1axios.get(`lib/authkeys/${id}`);
    },
    rotate(id) {
        return window.$nuxt.$gwapiv1axios.get(`lib/authkeys/${id}/rotate`);
    },
    delete(id, data) {
        return window.$nuxt.$gwapiv1axios.delete(`lib/authkeys/${id}`);
    },
    patch(id, data) {
        return window.$nuxt.$gwapiv1axios.patch(`lib/authkeys/${id}`, data);
    },
}

export default {
    info() {
        return window.$nuxt.$gwapiv1axios.get('system/info');
    },
}

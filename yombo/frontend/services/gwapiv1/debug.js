export default {
    debug(debug_type) {
        let uri = "debug?debug_type=" + debug_type;
        return window.$nuxt.$gwapiv1axios.get(uri);
    },
}

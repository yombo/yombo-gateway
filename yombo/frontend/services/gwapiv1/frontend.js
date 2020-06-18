export default {
    dashboard_navbar_items() {
        return window.$nuxt.$gwapiv1axios.get('frontend/dashboard_navbar_items');
    },
    globalitems_navbar_items() {
        return window.$nuxt.$gwapiv1axios.get('frontend/globalitems_navbar_items');
    },
}

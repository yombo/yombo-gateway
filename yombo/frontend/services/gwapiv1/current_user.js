export default {
    access_token() {
        console.log("current_user access token get....");
        return window.$nuxt.$gwapiv1axios.get('current_user/access_token');
    },
}

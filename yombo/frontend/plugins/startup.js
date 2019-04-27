export default () => {
  window.onNuxtReady((app) => {
    // this.$bus.$on('user_access_token', e => console.log("startup: " + e));
    window.$nuxt.$store.dispatch('access_token/fetch');
  });
}

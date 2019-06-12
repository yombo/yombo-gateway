export default () => {
  window.onNuxtReady((app) => {
    window.$nuxt.$store.dispatch('gateway/access_token/fetch');
  });
}

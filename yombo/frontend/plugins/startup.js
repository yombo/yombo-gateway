export default () => {
  window.onNuxtReady(() => {
    window.$nuxt.$store.dispatch('access_token/fetch');
  });
}

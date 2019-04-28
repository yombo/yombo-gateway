<script>
export default {
  fetch ({ params, redirect }) {
    redirect(301, window.$nuxt.localePath('dashboard-devices'))
  }
}
</script>

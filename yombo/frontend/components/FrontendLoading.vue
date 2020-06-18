<template>
  <span v-if="frontend_ready === null">
    <div class="vld-parent">
        <loading :active="true"
        :can-cancel="false"
        :is-full-page="true"
        loader="bars"
        background-color="#1C3B60"
        color="#EEE"
        :opacity=0.97></loading>
    </div>
    <div class="vld-parent">
        <loading :active="true"
        :can-cancel="false"
        :is-full-page="true"
        loader="spinner"
        background-color="#1C3B60"
        color="#2C82B4"
        :opacity=0.10></loading>
    </div>
  </span>
</template>

<script>
  import Loading from 'vue-loading-overlay'; // So we can dual loaders, vs in globalComponents.

  export default {
    components: {
      Loading,
    },
    computed: {
      frontend_ready () {
        return this.$store.state.nuxtenv.gateway_id;
      }
    }
  }
</script>

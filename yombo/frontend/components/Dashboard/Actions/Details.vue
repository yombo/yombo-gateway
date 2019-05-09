<template>
  <n-button @click.native="handleDetails()"
            class="edit"
            type="info"
            size="sm" round icon>
    <i class="fa fa-receipt"></i>
  </n-button>
</template>
<script>
export default {
  name: 'action-details',
  props: {
    path: String,
    id: String,
  },
  methods: {
    handleDetails() {
      this.$router.push(this.localePath(this.path)+"/"+this.id);
    },
  }
};
</script>
<style>
</style>

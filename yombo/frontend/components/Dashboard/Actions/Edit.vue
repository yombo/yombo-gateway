<template>
  <n-button @click.native="handleEdit()"
            class="edit"
            type="warning"
            size="sm" round icon>
    <i class="fa fa-edit"></i>
  </n-button>
</template>
<script>
export default {
  name: 'action-edit',
  props: {
    path: String,
    id: String,
  },
  methods: {
    handleEdit() {
      this.$router.push(this.localePath(this.path)+"/"+this.id);
    },
  }
};
</script>
<style>
</style>

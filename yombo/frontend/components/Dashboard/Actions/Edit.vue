<template>
  <span>
    <template v-if="this.size == 'small'">
      <n-button @click.native="handleEdit()"
                class="edit"
                type="success"
                size="sm" round icon>
        <i class="fa fa-edit"></i>
      </n-button>
    </template>
    <template v-else>
      <n-button @click.native="handleEdit()"
                class="edit"
                type="success"
                size="sm">
      {{ $t('ui.common.edit') }}
      </n-button>
    </template>
  </span>
</template>

<script>
export default {
  name: 'action-edit',
  props: {
    path: String,
    id: String,
    size: { type: String, default: "small"},
  },
  methods: {
    handleEdit() {
      this.$router.push(this.localePath({name:this.path + "-id-edit", params: {id: this.id}}));
    },
  }
};
</script>
<style>
</style>

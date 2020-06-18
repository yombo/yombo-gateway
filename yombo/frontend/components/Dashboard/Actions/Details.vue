<template>
  <span>
    <template v-if="size == 'small'">
      <n-button @click.native="handleDetails()"
                class="edit"
                type="info"
                size="sm" round icon>
        <i class="fa fa-receipt"></i>
      </n-button>
    </template>
    <template v-else>
      <n-button @click.native="handleDetails()"
                class="edit"
                type="info"
                size="sm">
      {{ $t('ui.common.details') }}
      </n-button>
    </template>
  </span>
</template>
<script>
export default {
  name: 'action-details',
  props: {
    path: String,
    id: String,
    size: { type: String, default: "small"},
  },
  methods: {
    handleDetails() {
      this.$router.push(this.localePath({name:this.path + "-id-details", params: {id: this.id}}));
    },
  }
};
</script>

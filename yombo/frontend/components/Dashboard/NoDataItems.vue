<template>
  <div v-else class="no-data-items">{{ $t('ui.common.no_data_items') }}</div>
</template>

<style lang="less" scoped>
.no-data-items {
  top: 0;
  bottom: 0;
  left: 0;
  right: 0;
  font-size: 25px;
  overflow: hidden;
  text-align: center;
  align-content: center;
  margin: 50px auto 200px;
}
</style>

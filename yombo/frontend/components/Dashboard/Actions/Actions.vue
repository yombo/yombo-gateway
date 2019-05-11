<template>
  <span>
    <template v-if="details">
      <action-details :path="path" :id="id" :size="size"/>
    </template>
    <template v-if="edit">
      <action-edit :path="path" :id="id" :size="size"/>
    </template>
    <template v-if="status">
      <template v-if="item.status == 1">
        <action-disable :dispatch="dispatch" :id="id"
                     :i18n="i18n" :item_label="item.full_label"
                     :size="size"/>
      </template>
      <template v-else>
        <action-enable dispatch="yombo/devices/enable" :id="item.id"
                     :i18n="i18n" :item_label="item.full_label"
                     :size="size"/>
      </template>
    </template>
    <template v-if="status">
      <action-delete dispatch="yombo/devices/delete" :id="id"
       :i18n="i18n" :item_label="item_label"
       :size="size"/>
    </template>
  </span>
</template>

<script>
import { ActionDelete, ActionDetails, ActionDisable, ActionEdit, ActionEnable } from '@/components/Dashboard/Actions';

export default {
  name: 'actions',
  components: {
    ActionDelete,
    ActionDetails,
    ActionDisable,
    ActionEdit,
    ActionEnable,
  },
  props: {
    path: String,
    dispatch: String,
    id: String,
    i18n: String,
    item_label: String,
    size: { type: String, default: "small"},
    enabledispatch: { type: String, default: ""},
    disabledispatch: { type: String, default: ""},
    deletedispatch: { type: String, default: ""},
    details: Boolean,
    edit: Boolean,
    status: Boolean,
    delete: Boolean,
  },
};
</script>
<style>
</style>

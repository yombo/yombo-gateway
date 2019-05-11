<template>
  <div class="row">
    <div class="col-md-12">
      <card card-body-classes="table-full-width">
        <div slot="header">
        <h4 class="card-title">
           {{ $t('ui.common.edit') }} {{ $t('ui.common.device') }}: {{item.full_label}}
          <div class="pull-right">
            <action-details path="dashboard-devices" :id="item.id" size="regular"/>
            <template v-if="item.status == 1">
              <action-disable dispatch="yombo/devices/disable" :id="item.id"
                           i18n="device" :item_label="item.full_label"
                           size="regular"/>
            </template>
            <template v-else>
              <action-enable dispatch="yombo/devices/enable" :id="item.id"
                           i18n="device" :item_label="item.full_label"
                           size="regular"/>
            </template>
            <action-delete dispatch="yombo/devices/delete" :id="item.id"
             i18n="device" :item_label="item.full_label"
             size="regular"/>

          </div>
         </h4>
        </div>
        <div class="card-body">
          Device: {{id}}
          {{item.full_label}}
        </div>
      </card>
    </div>

  </div>
</template>
<script>
import { ActionDelete, ActionDetails, ActionDisable, ActionEnable } from '@/components/Dashboard/Actions';

import Device from '@/models/device'

export default {
  layout: 'dashboard',
  components: {
    ActionDelete,
    ActionDetails,
    ActionDisable,
    ActionEnable,
  },
  data() {
    return {
      id: this.$route.params.id,
      display_age: '0 seconds',
    };
  },
  computed: {
    item () {
      return Device.query().where('id', this.id).first()
    },
  },
  mounted () {
    this.$store.dispatch('yombo/devices/fetchOne', this.id);
  },
};
</script>

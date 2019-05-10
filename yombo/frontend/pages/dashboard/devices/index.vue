<template>
  <div class="row">
    <div class="col-md-12">
      <card card-body-classes="table-full-width">
        <div slot="header">
          <div class="fa-pull-right">
            <nuxt-link class="navbar-brand fa-pull-right" :to="localePath('dashboard-devices-add')">
              <button type="button" class="btn btn-info btn-sm" data-dismiss="modal">
                <i class="fas fa-plus-circle fa-pull-left" style="font-size: 1.5em;"></i> &nbsp; Add new</a>
                </button>
            </nuxt-link>
            <br>
            <el-input
                  class="fa-pull-right"
                  v-model="search"
                  size="mini"
                  :placeholder="$t('ui.common.search_ddd')"/>
          </div>
          <h4 class="card-title">
            {{ $t('ui.navigation.devices') }}
          </h4>
          <last-updated refresh="yombo/devices/fetch" getter="yombo/devices/display_age"/>
        </div>
        <div class="card-body">
          <el-table
            :data="items.filter(data => !search
             || data.label.toLowerCase().includes(search.toLowerCase())
             || data.description.toLowerCase().includes(search.toLowerCase())
             )"
          >
            <el-table-column :label="$t('ui.common.label')" property="full_label"></el-table-column>
            <el-table-column :label="$t('ui.common.description')" property="description"></el-table-column>
            <el-table-column :label="$t('ui.common.location')" property="full_location"></el-table-column>
            <el-table-column
              align="right" :label="$t('ui.common.actions')">
              <div slot-scope="props" class="table-actions">
                <action-details path="dashboard-devices" :id="props.row.id"/>
                <action-edit path="dashboard-devices" :id="props.row.id"/>
                <template v-if="props.row.status == 1">
                  <action-disable dispatch="yombo/devices/disable" :id="props.row.id"
                               i18n="device" :item_label="props.full_label"/>
                </template>
                <template v-else>
                  <action-enable dispatch="yombo/devices/enable" :id="props.row.id"
                               i18n="device" :item_label="props.row.full_label"/>
                </template>
                  <action-delete dispatch="yombo/devices/delete" :id="props.row.id"
                               i18n="device" :item_label="props.row.full_label"/>
              </div>
            </el-table-column>
          </el-table>
        </div>
      </card>
    </div>

  </div>
</template>
<script>
import { ActionDelete, ActionDetails, ActionDisable, ActionEdit, ActionEnable } from '@/components/Dashboard/Actions';
import LastUpdated from '@/components/Dashboard/LastUpdated.vue'

import { Table, TableColumn } from 'element-ui';

import Device from '@/models/device'

export default {
  layout: 'dashboard',
  components: {
    [Table.name]: Table,
    [TableColumn.name]: TableColumn,
    ActionDelete,
    ActionDetails,
    ActionDisable,
    ActionEdit,
    ActionEnable,
    LastUpdated,
  },
  data() {
    return {
      search: '',
    };
  },
  computed: {
    items () {
      return Device.query().orderBy('full_label', 'desc').get()
    },
  },
  mounted () {
    this.$store.dispatch('yombo/devices/refresh');
    this.$store.dispatch('yombo/locations/refresh');
  },
};
</script>

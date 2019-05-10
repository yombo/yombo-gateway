<template>
  <div class="row">
    <div class="col-md-12">
      <card card-body-classes="table-full-width">
        <div slot="header">
          <h4 class="card-title">
             {{ $t('ui.navigation.device_commands') }}
          </h4>
          <div class="fa-pull-right">
            <el-input
                  class="fa-pull-right"
                  v-model="search"
                  size="mini"
                  :placeholder="$t('ui.common.search_ddd')"/>
          </div>
          <last-updated refresh="gateway/device_commands/fetch" getter="gateway/device_commands/display_age"/>
        </div>
        <div class="card-body">
          <el-table
             :data="items.filter(data => !search
             || data.id.toLowerCase().includes(search.toLowerCase())
             || data.gateway_id.toLowerCase().includes(search.toLowerCase())
             || data.source.toLowerCase().includes(search.toLowerCase())
             // || data.value_human.toLowerCase().includes(search.toLowerCase())
             )"
          >
            <el-table-column :label="$t('ui.common.request_id')" property="id"></el-table-column>
            <el-table-column :label="$t('ui.common.gateway')">
              <div slot-scope="props" class="table-actions">
                {{getGateway(props.row.source_gateway_id).label}}
              </div>
            </el-table-column>
            <el-table-column :label="$t('ui.common.device')">
              <div slot-scope="props" class="table-actions">
                {{getDevice(props.row.device_id).full_label}}
              </div>
            </el-table-column>
            <el-table-column :label="$t('ui.common.status')" property="status"></el-table-column>
            <el-table-column :label="$t('ui.common.created_at')" property="created_at"></el-table-column>
            <el-table-column
              align="right" :label="$t('ui.common.actions')">
              <div slot-scope="props" class="table-actions">
                <action-details path="dashboard-device_commands" :id="props.row.id"/>
              </div>
            </el-table-column>

          </el-table>
        </div>
      </card>
    </div>

  </div>
</template>
<script>
import { ActionDetails } from '@/components/Dashboard/Actions';
import LastUpdated from '@/components/Dashboard/LastUpdated.vue'

import Device from '@/models/device'
import Gateway from '@/models/gateway'

import { Table, TableColumn } from 'element-ui';

export default {
  layout: 'dashboard',
  components: {
    [Table.name]: Table,
    [TableColumn.name]: TableColumn,
    ActionDetails,
    LastUpdated,
  },
  data() {
    return {
      search: '',
    };
  },
  computed: {
    items () {
      let source = this.$store.state.gateway.device_commands.data;
      let results = [];
      let cache = {}
      let atom = {}
      let gateway_label = ""
      let gateawy = null

      Object.keys(source).forEach(key => {
        results.push(source[key]);
      });
      return results
    },
  },

  methods: {
    getDevice(id) {
      // console.log("get device...." + id)
      return Device.query().where('id', id).first();
    },
    getGateway(id) {
      return Gateway.query().where('id', id).first();
    },
  },
  mounted () {
    this.$store.dispatch('gateway/device_commands/refresh');
  },
};
</script>

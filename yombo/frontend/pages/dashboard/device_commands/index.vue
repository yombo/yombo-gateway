<template>
  <dashboard-display-index
    :pageTitle="$t('ui.navigation.device_commands')"
    addPath="dashboard-device_commands-add"
    displayAgePath="gateway/device_commands/display_age"
    :dashboardFetchData="dashboardFetchData"
    :dashboardDisplayItems="dashboardDisplayItems"
    :apiErrors="apiErrors"
  >
    <span v-if="dashboardDisplayItems">
      <dashboard-table-pagination
          tableIndex="1"
          tableName="indexTable1"
          position="top"
          :rowCount="dashboardQueriedData.length"
        >
      </dashboard-table-pagination>
      <b-table striped hover
               id="indexTable1"
               :items="dashboardQueriedData"
               :per-page="dashboardTableRowsPerPage"
               :current-page="dashboardTablePage1"
               :fields="tableColumns1"
               small
               >
        <template v-slot:cell(actions)="data">
          <dashboard-row-actions
            :typeLabel="$t('ui.common.roles')"
            :displayItem="data.item"
            :itemLabel="data.item.id"
            :id="data.item.id"
            detailIcon="dashboard-device_commands-id-details"
            deleteIcon="gateway/device_commands/delete"
          ></dashboard-row-actions>
        </template>
      </b-table>
      <dashboard-table-pagination
          tableIndex="1"
          tableName="indexTable1"
          position="bottom"
          :rowCount="dashboardQueriedData.length"
        >
      </dashboard-table-pagination>
    </span>
  </dashboard-display-index>
</template>

<script>
  import Fuse from 'fuse.js';

  import { dashboardApiIndexMixin } from "@/mixins/dashboardApiIndexMixin";

  import { GW_Location } from '@/models/location'

  export default {
    layout: 'dashboard',
    mixins: [dashboardApiIndexMixin],
    data() {
      return {
        dashboardBusModel: "device_commands",
        tableColumns1: [
          {key: 'device_id', label: this.$i18n.t('ui.common.device') },
          {key: 'command_id', label: this.$i18n.t('ui.common.command') },
          {key: 'status',  label: this.$i18n.t('ui.common.status') },
          {key: 'created_at',  label: this.$i18n.t('ui.common.created_at') },
          {key: 'actions',  label: this.$i18n.t('ui.common.actions') },
        ],
      }
    },
    methods: {
      dashboardGetFuseData() {
        this.dashboardDisplayItems = GW_Location.query()
                                       .where('location_type', 'area')
                                       .orderBy('label', 'asc')
                                       .get();
        this.dashboardFuseSearch = new Fuse(this.dashboardDisplayItems, {
          keys: [
            { name: 'label', weight: 0.5 },
            { name: 'machine_label', weight: 0.3 },
            { name: 'description', weight: 0.2 },
          ]
        });
      }
    },
  };
</script>


<template>
  <div class="row">
    <div class="col-md-12">
      <card card-body-classes="table-full-width">
        <div slot="header">
          <div class="d-flex bd-highlight">
            <div class="flex-grow-1 bd-highlight">
              <h4 class="card-title">
               {{ $t('ui.navigation.device_commands') }}
              </h4>
            </div>
            <div class="bd-highlight">
              <nuxt-link class="navbar-brand fa-pull-right" :to="localePath('dashboard-device_commands-add')">
                <button type="button" class="btn btn-info btn-sm" data-dismiss="modal">
                  <i class="fas fa-plus-circle fa-pull-left" style="font-size: 1.5em;"></i> &nbsp; Add new
                </button>
              </nuxt-link>
            </div>
          </div>
          <div class="d-flex bd-highlight">
            <div class="flex-grow-1 bd-highlight">
<!--              <data-last-updated refresh="gateway/device_commands/fetch" getter="gateway/device_commands/display_age"/>-->
            </div>
            <div class="bd-highlight">
              <fg-input>
                <el-input type="search"
                          class="mb-0"
                          clearable
                          prefix-icon="el-icon-search"
                          style="width: 200px"
                          placeholder="Search device commands..."
                          v-model="dashboardSearchQuery"
                          aria-controls="datatables">
                </el-input>
              </fg-input>
            </div>
          </div>
        </div>
        <div v-if="dashboardDisplayItems !== null && dashboardDisplayItems.length == 0"><no-data-items></no-data-items></div>
        <div v-else-if="dashboardDisplayItems === null"><data-loading></data-loading></div>
        <div class="card-body" v-else>
          <el-table stripe :data="dashboardQueriedData">
            <el-table-column :label="$t('ui.common.device')" property="device_id"></el-table-column>
            <el-table-column :label="$t('ui.common.command')" property="command_id"></el-table-column>
            <el-table-column :label="$t('ui.common.status')" property="status"></el-table-column>
            <el-table-column :label="$t('ui.common.created_at')" property="created_at"></el-table-column>
            <el-table-column
              align="right" :label="$t('ui.common.actions')">
              <div slot-scope="props" class="table-actions">
                <action-details path="dashboard-device_commands" :id="props.row.id"/>
                <action-delete path="dashboard-device_commands-delete" :id="props.row.id"
                               i18n="area" :item_label="props.label"/>
              </div>
            </el-table-column>
          </el-table>
        </div>
      </card>
    </div>

  </div>
</template>

<script>
import { Table, TableColumn, Select, Option } from 'element-ui';
import { ActionDelete, ActionDetails, ActionDisable, ActionEdit, ActionEnable } from '@/components/Dashboard/Actions';
import Fuse from 'fuse.js';

import { GW_Device_Command } from '@/models/device_command'

export default {
  layout: 'dashboard',
  components: {
    [Select.name]: Select,
    [Option.name]: Option,
    [Table.name]: Table,
    [TableColumn.name]: TableColumn,
    ActionDelete,
    ActionDetails,
    ActionDisable,
    ActionEdit,
    ActionEnable,
  },
  computed: {
    dashboardQueriedData() {
      let result = this.dashboardDisplayItems;
      if (this.dashboardSearchQuery.length > 0) {
        result = this.dashboardSearchedData;
      }
      return result;
    },
  },
  data() {
    return {
      dashboardSearchQuery: '',
      dashboardDisplayItems: null,
      dashboardSearchedData: [],
    };
  },
  beforeMount() {
    let that = this;
    this.$store.dispatch('gateway/devices/refresh');
    this.$store.dispatch('gateway/commands/refresh');
    this.$store.dispatch('gateway/device_commands/fetch')
      .then(function() {
        that.dashboardDisplayItems = GW_Device_Command.query()
                                                .orderBy('created_at', 'desc')
                                                .get();
        that.dashboardFuseSearch = new Fuse(that.dashboardDisplayItems, {
          keys: [
            { name: 'device_id', weight: 0.5 },
            { name: 'command_id', weight: 0.5 },
          ]
        });

      });
  },
  watch: {
    dashboardSearchQuery(value) {
      let result = this.dashboardDisplayItems;
      if (value !== '') {
        result = this.dashboardFuseSearch.search(this.dashboardSearchQuery);
      }
      this.dashboardSearchedData = result;
    }
  }
};
</script>

<style lang="less" scoped>
  .input-group .form-control {
    margin-bottom: 0px;
  }
</style>

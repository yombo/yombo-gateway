<template>
  <dashboard-display-index
    :pageTitle="$t('ui.navigation.discovered')"
    displayAgePath="gateway/discovery/display_age"
    :dashboardFetchData="dashboardFetchData"
    :dashboardDisplayItems="dashboardDisplayItems"
    :apiErrors="apiErrors"
  >
    <span v-if="dashboardDisplayItems">
      <b-tabs card content-class="">
        <b-tab title="This GW" active>
          <el-table
             :data="dashboardQueriedData.filter(data => data
             && data.gateway_id == gateway_id
             )">
            <el-table-column :label="$t('ui.common.label')" property="label"></el-table-column>
            <el-table-column :label="$t('ui.common.description')" property="description"></el-table-column>
            <el-table-column :label="$t('ui.common.mfr')" property="mfr"></el-table-column>
          </el-table>
        </b-tab>
        <b-tab title="Cluster">
          <el-table
             :data="dashboardQueriedData.filter(data => data
             && data.gateway_id != gateway_id
             )">
            <el-table-column align="right" :label="$t('ui.common.gateway')">
              <div slot-scope="props">
                {{gateway(props.row.gateway_id)}}
              </div>
            </el-table-column>
            <el-table-column :label="$t('ui.common.label')" property="label"></el-table-column>
            <el-table-column :label="$t('ui.common.description')" property="description"></el-table-column>
            <el-table-column :label="$t('ui.common.mfr')" property="mfr"></el-table-column>
          </el-table>
        </b-tab>
      </b-tabs>
    </span>
  </dashboard-display-index>
</template>

<script>
  import { dashboardApiIndexMixin } from "@/mixins/dashboardApiIndexMixin";
  import Fuse from 'fuse.js';

  import { GW_Discovery } from '@/models/discovery'

  export default {
    layout: 'dashboard',
    mixins: [dashboardApiIndexMixin],
    data() {
      return {
        dashboardBusModel: "discovery",
        labels: {
          label: this.$t('ui.common.label') +  '<hr class="dotted compact">' + this.$t('ui.common.machine_label'),
          details: 'mfr<hr class="dotted compact">model<hr class="dotted compact">',
          times: this.$t('ui.common.discovered_at') + '<hr class="dotted compact">' + this.$t('ui.common.last_seen') +
            '<hr class="dotted compact">' + this.$t('ui.common.created_at'),
        },
      };
    },
    methods: {
      dashboardGetFuseData() {
        this.dashboardDisplayItems = GW_Discovery.query()
                                        .orderBy('label', 'asc')
                                        .get();
        this.dashboardFuseSearch = new Fuse(this.dashboardDisplayItems, {
          keys: [
            { name: 'label', weight: 0.5 },
            { name: 'machine_label', weight: 0.4 },
            { name: 'description', weight: 0.1 },
          ]
        });
      }
    },
  };
</script>

<style lang="less" scoped>
  .input-group .form-control {
    margin-bottom: 0px;
  }
</style>

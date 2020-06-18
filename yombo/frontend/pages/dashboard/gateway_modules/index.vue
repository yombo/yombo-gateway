<template>
  <dashboard-display-index
    :pageTitle="$t('ui.navigation.gateway_modules')"
    addPath="dashboard-gateway_modules-add"
    displayAgePath="gateway/gateway_modules/display_age"
    :dashboardFetchData="dashboardFetchData"
    :dashboardDisplayItems="dashboardDisplayItems"
    :apiErrors="apiErrors"
  >
    <span v-if="dashboardDisplayItems">
      <el-table stripe :data="dashboardQueriedData">
        <el-table-column
          :min-width="100"
          :label="$t('ui.common.label')"
          property="label"></el-table-column>
        <el-table-column
          :min-width="120"
          :label="$t('ui.common.description')"
          property="short_description"></el-table-column>
        <el-table-column
          :min-width="50"
          :label="$t('ui.common.source')"
          property="load_source"></el-table-column>
        <el-table-column
          :min-width="75"
          :label="$t('ui.common.updated_at')"
          property="updated_at"></el-table-column>
        <el-table-column
          align="right" :label="$t('ui.common.actions')">
          <div slot-scope="props" class="table-actions">
            <dashboard-row-actions
              :typeLabel="$t('ui.common.area')"
              :displayItem="props.row"
              :itemLabel="props.row.id"
              :id="props.row.id"
              detailIcon="dashboard-gateway_modules-id-details"
              editIcon="dashboard-gateway_modules-id-edit"
              deleteIcon="gateway/gateway_modules/delete"
            ></dashboard-row-actions>
          </div>
        </el-table-column>
      </el-table>
    </span>
  </dashboard-display-index>
</template>

<script>
  import { dashboardApiIndexMixin } from "@/mixins/dashboardApiIndexMixin";
  import Fuse from 'fuse.js';

  import { GW_Module } from '@/models/module'

  export default {
    layout: 'dashboard',
    mixins: [dashboardApiIndexMixin],
    data() {
      return {
        dashboardBusModel: "locations",
      }
    },
    methods: {
      dashboardGetFuseData() {
        this.dashboardDisplayItems = GW_Module.query()
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

<style lang="less" scoped>
  .input-group .form-control {
    margin-bottom: 0px;
  }
</style>

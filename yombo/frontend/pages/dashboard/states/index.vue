<template>
  <dashboard-display-index
    :pageTitle="$t('ui.navigation.states')"
    addPath="dashboard-states-add"
    displayAgePath="gateway/states/display_age"
    :dashboardFetchData="dashboardFetchData"
    :dashboardDisplayItems="dashboardDisplayItems"
    :apiErrors="apiErrors"
  >
    <span v-if="dashboardDisplayItems">
      <el-table stripe :data="dashboardQueriedData">
        <el-table-column
          :min-width="100"
          :label="$t('ui.common.state')"
          property="id"></el-table-column>
        <el-table-column
          :min-width="100"
          :label="$t('ui.common.value')"
          property="value_human"></el-table-column>
        <el-table-column
          :min-width="50"
          :label="$t('ui.common.updated_at')">
          <div slot-scope="props" class="table-actions">
            {{props.row.updated_at | epoch_to_datetime }}
          </div>
        </el-table-column>
        <el-table-column
          :min-width="50"
          align="right"
          :label="$t('ui.common.actions')"
        >
          <div slot-scope="props" class="table-actions">
            <dashboard-row-actions
              :typeLabel="$t('ui.common.state')"
              :displayItem="props.row"
              :itemLabel="props.row.id"
              :id="props.row.id"
              detailIcon="dashboard-states-id-details"
              editIcon="dashboard-states-id-edit"
              deleteIcon="gateway/states/delete"
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

  import { GW_State } from '@/models/state'

  export default {
    layout: 'dashboard',
    mixins: [dashboardApiIndexMixin],
    data() {
      return {
        dashboardBusModel: "states",
      }
    },
    methods: {
      dashboardGetFuseData() {
        this.dashboardDisplayItems = GW_State.query()
                                    .orderBy('id', 'asc')
                                    .get();
        this.dashboardFuseSearch = new Fuse(this.dashboardDisplayItems, {
          keys: [
            { name: 'id', weight: 0.5 },
            { name: 'value', weight: 0.25 },
            { name: 'value_human', weight: 0.25 },
          ]
        });
      },
    },
  };
</script>

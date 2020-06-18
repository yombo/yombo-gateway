<template>
    <dashboard-display-index
    :pageTitle="$t('ui.navigation.scenes')"
    addPath="dashboard-scenes-add"
    displayAgePath="gateway/scenes/display_age"
    :dashboardFetchData="dashboardFetchData"
    :dashboardDisplayItems="dashboardDisplayItems"
    :apiErrors="apiErrors"
  >
    <span v-if="dashboardDisplayItems">
      <el-table stripe :data="dashboardQueriedData">
        <el-table-column :label="$t('ui.common.label')" property="label"></el-table-column>
        <el-table-column :label="$t('ui.common.description')" property="rule.config.description"></el-table-column>
        <el-table-column :label="$t('ui.common.enabled')">
          <div slot-scope="props">
            {{props.row.status == 1}}
          </div>
        </el-table-column>
        <el-table-column
          :min-width="50"
          :label="$t('ui.common.updated_at')">
          <div slot-scope="props" class="table-actions">
            {{props.row }}
            {{props.row.updated_at | epoch_to_datetime }}
          </div>
        </el-table-column>
        <el-table-column
          align="right" :label="$t('ui.common.actions')">
          <div slot-scope="props" class="table-actions">
            <dashboard-row-actions
              :typeLabel="$t('ui.common.automation_rule')"
              :displayItem="props.row"
              :itemLabel="props.row.id"
              :id="props.row.id"
              detailIcon="dashboard-scenes-id-details"
              editIcon="dashboard-scenes-id-edit"
              deleteIcon="gateway/scenes/delete"
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

  import { GW_Scene } from '@/models/scene'

  export default {
    layout: 'dashboard',
    mixins: [dashboardApiIndexMixin],
    data() {
      return {
        dashboardBusModel: "scenes",
      };
    },
    methods: {
      dashboardGetFuseData() {
        this.dashboardDisplayItems = GW_Scene.query()
                                    .orderBy('label', 'asc')
                                    .get();
        this.dashboardFuseSearch = new Fuse(this.dashboardDisplayItems, {
          keys: [
            { name: 'label', weight: 0.5 },
            { name: 'machine_label', weight: 0.5 },
          ]
        });
      },
      dashboardFetchData(forceFetch = true) {
        let that = this;
        this.apiErrors = null;
        let fetchType = "refresh";
        if (forceFetch)
          fetchType = "fetch";
        this.$store.dispatch(`gateway/scenes/${fetchType}`)
          .then(function() {
            that.dashboardGetFuseData();
          })
          .catch(error => {
            that.apiErrors = this.$handleApiErrorResponse(error);
          });
      }
    },
  };
</script>

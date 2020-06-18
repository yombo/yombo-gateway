<template>
  <dashboard-display-index
    :pageTitle="$t('ui.navigation.gateways')"
    addPath="dashboard-locations-add"
    displayAgePath="gateway/locations/display_age"
    :dashboardFetchData="dashboardFetchData"
    :dashboardDisplayItems="dashboardDisplayItems"
    :apiErrors="apiErrors"
  >
    <span v-if="dashboardDisplayItems">
      <el-table stripe :data="dashboardQueriedData">
            <el-table-column
              :label="$t('ui.common.label')"
              property="label">
              <div slot-scope="props" class="table-actions">
                <div
                  :title="props.row.label"
                  v-b-popover.hover.right.html="
                  'Gateway ID: ' + props.row.id +
                  '<br>Machine Label: ' + props.row.machine_label +
                  '<br>DNS: ' + props.row.dns_name +
                  '<br>IPv4: ' + props.row.internal_ipv4 + ' / ' + props.row.external_ipv4 +
                  '<br>IPv4: ' + props.row.internal_ipv6"
                  delay="10"
                >
                  {{props.row.label}}
                </div>
              </div>
            </el-table-column>
            <el-table-column
              :label="$t('ui.common.parent')">
              <div slot-scope="props" class="table-actions">
                {{props.row.master_gateway_id}}
<!--             this is causing it fail. and wierdly reload... -->
<!--                {{ gateway(props.row.master_gateway_id)["label"] }}-->
<!--                {{ gateway(props.row.master_gateway_id) }}-->
              </div>
            </el-table-column>
            <el-table-column
              :min-width="120"
              :label="$t('ui.common.description')"
              property="description">
            </el-table-column>
        <el-table-column
          align="right" :label="$t('ui.common.actions')">
          <div slot-scope="props" class="table-actions">
            <dashboard-row-actions
              :typeLabel="$t('ui.common.area')"
              :displayItem="props.row"
              :itemLabel="props.row.id"
              :id="props.row.id"
              detailIcon="dashboard-gateways-id-details"
              editIcon="dashboard-gateways-id-edit"
              disableIcon="gateway/gateways/disable"
              enableIcon="gateway/gateways/enable"
              deleteIcon="gateway/gateways/delete"
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

  import { GW_Gateway } from '@/models/gateway'

  export default {
    layout: 'dashboard',
    mixins: [dashboardApiIndexMixin],
    data() {
      return {
        dashboardBusModel: "locations",
      }
    },
    methods: {
      gateway(gateway_id) {
        console.log(`looking for gateway: ${gateway_id}`);
        if (gateway_id)
          return GW_Gateway.query().where('id', gateway_id).first();
        console.log("returning empty gateway.");
        return {label: ""}
      },
      dashboardGetFuseData() {
        this.dashboardDisplayItems = GW_Gateway.query()
                                      .orderBy('master_gateway_id')
                                      .orderBy('is_master', 'desc')
                                      .orderBy('label', 'asc')
                                      .get();
        this.dashboardFuseSearch = new Fuse(this.dashboardDisplayItems, {
          keys: [
            { name: 'label', weight: 0.7 },
            { name: 'description', weight: 0.3 },
          ]
        });
      }
    },
  };
</script>

<template>
  <dashboard-display-index
    :pageTitle="$t('ui.navigation.users')"
    addPath="dashboard-users-add"
    displayAgePath="gateway/users/display_age"
    :dashboardFetchData="dashboardFetchData"
    :dashboardDisplayItems="dashboardDisplayItems"
    :apiErrors="apiErrors"
  >
    <span v-if="dashboardDisplayItems">
      <b-tabs nav-class="nav-tabs-primary" v-model="tabAnchorIndex">
        <b-tab title="This GW" href="#local" @click="tabAnchorChange('local')">
          <el-table
             :data="dashboardQueriedData">
            <el-table-column
              :min-width="100"
              :label="$t('ui.common.name')"
              property="name">
            </el-table-column>
            <el-table-column
              :min-width="100"
              :label="$t('ui.common.email')"
              property="email">
            </el-table-column>
            <el-table-column
              align="right" :label="$t('ui.common.actions')">
              <div slot-scope="props" class="table-actions">
                <dashboard-row-actions
                  :typeLabel="$t('ui.common.location')"
                  :displayItem="props.row"
                  :itemLabel="props.row.id"
                  :id="props.row.id"
                  detailIcon="dashboard-users-id-details"
                  editIcon="dashboard-users-id-edit"
                  deleteIcon="gateway/users/delete"
                ></dashboard-row-actions>
              </div>
            </el-table-column>
          </el-table>
        </b-tab>
        <b-tab title="Cluster" href="#cluster" @click="tabAnchorChange('cluster')">
          <el-table
             :data="dashboardQueriedData.filter(data => data
             && data.gateway_id != gateway_id
             )">
            <el-table-column align="right" :label="$t('ui.common.gateway')">
              <div slot-scope="props">
                {{gateway(props.row.gateway_id)}}
              </div>
            </el-table-column>
            <el-table-column :label="$t('ui.common.location')" property="full_location"></el-table-column>
            <el-table-column :label="$t('ui.common.label')" property="label"></el-table-column>
            <el-table-column :label="$t('ui.common.description')" property="description"></el-table-column>
            <el-table-column
              align="right" :label="$t('ui.common.actions')">
              <div slot-scope="props" class="table-actions">
                <dashboard-row-actions
                  :typeLabel="$t('ui.common.location')"
                  :displayItem="props.row"
                  :itemLabel="props.row.id"
                  :id="props.row.id"
                  detailIcon="dashboard-devices-id-details"
                  editIcon="dashboard-devices-id-edit"
                  deleteIcon="gateway/devices/delete"
                  disableIcon="gateway/devices/enable"
                  enableIcon="gateway/devices/disable"
                ></dashboard-row-actions>
              </div>
            </el-table-column>
          </el-table>
        </b-tab>
      </b-tabs>
    </span>
  </dashboard-display-index>


<!--  <div class="row" v-if="users">-->
<!--    <div class="col-md-12">-->
<!--      <card card-body-classes="table-full-width">-->
<!--        <div slot="header">-->
<!--          <div class="d-flex bd-highlight">-->
<!--            <div class="flex-grow-1 bd-highlight">-->
<!--              <h4 class="card-title">-->
<!--               {{ $t('ui.navigation.users') }}-->
<!--              </h4>-->
<!--            </div>-->
<!--            <div class="bd-highlight">-->
<!--              <nuxt-link class="navbar-brand fa-pull-right" :to="localePath('dashboard-users-add')">-->
<!--                <button type="button" class="btn btn-info btn-sm" data-dismiss="modal">-->
<!--                  <i class="fas fa-plus-circle fa-pull-left" style="font-size: 1.5em;"></i> &nbsp; Add new-->
<!--                </button>-->
<!--              </nuxt-link>-->
<!--            </div>-->
<!--          </div>-->
<!--          <div class="d-flex bd-highlight">-->
<!--            <div class="flex-grow-1 bd-highlight">-->
<!--              <last-updated refresh="gateway/users/fetch" getter="gateway/users/display_age"/>-->
<!--            </div>-->
<!--            <div class="bd-highlight">-->
<!--              <fg-input>-->
<!--                <el-input type="search"-->
<!--                          class="mb-0"-->
<!--                          clearable-->
<!--                          prefix-icon="el-icon-search"-->
<!--                          style="width: 200px"-->
<!--                          placeholder="Search users..."-->
<!--                          v-model="dashboardSearchQuery"-->
<!--                          aria-controls="datatables">-->
<!--                </el-input>-->
<!--              </fg-input>-->
<!--            </div>-->
<!--          </div>-->
<!--        </div>-->
<!--        <div v-if="dashboardDisplayItems !== null && dashboardDisplayItems.length == 0"><no-items></no-items></div>-->
<!--        <div v-else-if="dashboardDisplayItems === null"><spinner></spinner></div>-->
<!--        <div class="card-body" v-else>-->
<!--          <el-table stripe :data="dashboardQueriedData">-->
<!--            <el-table-column-->
<!--              :min-width="100"-->
<!--              :label="$t('ui.common.name')"-->
<!--              property="name">-->
<!--            </el-table-column>-->
<!--            <el-table-column-->
<!--              :min-width="100"-->
<!--              :label="$t('ui.common.email')"-->
<!--              property="email">-->
<!--            </el-table-column>-->
<!--            <el-table-column-->
<!--              :min-width="80"-->
<!--              align="right" :label="$t('ui.common.actions')">-->
<!--              <div slot-scope="props" class="table-actions">-->
<!--                <action-details path="dashboard-users" :id="props.row.id"/>-->
<!--                <action-edit path="dashboard-users" :id="props.row.id"/>-->
<!--                <action-delete path="dashboard-users-delete" :id="props.row.id"-->
<!--                               i18n="area" :item_label="props.label"/>-->
<!--              </div>-->
<!--            </el-table-column>-->
<!--          </el-table>-->
<!--        </div>-->
<!--      </card>-->
<!--    </div>-->

<!--  </div>-->
</template>

<script>
  import { dashboardApiIndexMixin } from "@/mixins/dashboardApiIndexMixin";
  import Fuse from 'fuse.js';

  import { GW_User } from '@/models/user'

  export default {
    layout: 'dashboard',
    mixins: [dashboardApiIndexMixin],
    methods: {
      dashboardFetchData(forceFetch = true) {
        let that = this;
        this.apiErrors = null;
        let fetchType = "refresh";
        if (forceFetch)
          fetchType = "fetch";
        this.$store.dispatch(`gateway/users/${fetchType}`)
          .then(function() {
            that.dashboardDisplayItems = GW_User.query()
                                       .orderBy('name', 'asc')
                                       .get();
            that.dashboardFuseSearch = new Fuse(that.dashboardDisplayItems, {
              keys: [
                { name: 'name', weight: 0.6 },
                { name: 'email', weight: 0.4 },
              ]
            });
          })
          .catch(error => {
            that.apiErrors = this.$handleApiErrorResponse(error);
          });
      }
    },
    mounted() {
      this.$store.dispatch(`gateway/users/refresh`);
    }
  };
</script>

<style lang="less" scoped>
  .input-group .form-control {
    margin-bottom: 0px;
  }
</style>

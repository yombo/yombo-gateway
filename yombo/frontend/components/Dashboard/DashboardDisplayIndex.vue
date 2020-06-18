<template>
  <div class="row">
    <div class="col-md-12">
      <card card-body-classes="table-full-width">
        <div slot="header">
          <div class="d-flex bd-highlight">
            <div class="flex-grow-1 bd-highlight">
              <h5 class="card-title">
               {{ pageTitle }}
              </h5>
            </div>
            <div class="bd-highlight" v-if="addPath">
              <nuxt-link class="navbar-brand fa-pull-right" :to="localePath(addPath)">
                <button type="button" class="btn btn-info btn-sm" data-dismiss="modal">
                  <i class="fas fa-plus-circle fa-pull-left" style="font-size: 1.5em;"></i> &nbsp; {{ $t("ui.common.add_new") }}
                </button>
              </nuxt-link>
            </div>
          </div>
          <div class="d-flex bd-highlight">
            <div class="flex-grow-1 bd-highlight" v-if="dashboardFetchData && displayAgePath">
              <dashboard-data-last-updated :displayAgePath="displayAgePath" :dashboardFetchData="dashboardFetchData"/>
            </div>
            <div class="bd-highlight" v-if="$parent.$parent.apiErrors == null">
              <fg-input>
                <el-input type="search"
                          class="mb-0"
                          clearable
                          prefix-icon="el-icon-search"
                          style="width: 200px"
                          :placeholder="$t('ui.common.search_ddd')"
                          v-model="$parent.dashboardSearchQuery"
                          aria-controls="datatables">
                </el-input>
              </fg-input>
            </div>
          </div>
        </div>
        <div class="card-body">
          <dashboard-display-data :displayItem="dashboardDisplayItems" :apiErrors="apiErrors">
            <slot></slot>
          </dashboard-display-data>
        </div>
      </card>
    </div>
  </div>
</template>

<script>
  import DashboardDataLastUpdated from "./DashboardDataLastUpdated";
  import DashboardDisplayData from '@/components/Dashboard/DashboardDisplayData.vue';

  export default {
    name: 'dashboard-display-index',
    components: {
      DashboardDataLastUpdated,
      DashboardDisplayData,
    },
    props: {
      pageTitle: String,
      addPath: String,
      displayAgePath: String,
      dashboardFetchData: Function,
      dashboardDisplayItems: Array,
      apiErrors: Array,
    },
  };
</script>

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
            <div class="bd-highlight pull-right">
              <dashboard-row-actions
                :typeLabel="$t('ui.common.state')"
                :item="displayItem"
                :id="id"
                :itemLabel="itemLabel"
                urlPrefix="dashboard-states"
                :deleteIcon="deleteIcon"
                :detailIcon="detailIcon"
                :editIcon="editIcon"
                :refreshIcon="refreshIcon"
                :dashboardFetchData="dashboardFetchData"
              ></dashboard-row-actions>
            </div>
          </div>
        </div>
        <div class="card-body">
          <dashboard-display-data :displayItem="displayItem" :apiErrors="apiErrors">
            <slot></slot>
          </dashboard-display-data>
        </div>
      </card>
    </div>
  </div>
</template>

<script>
  import DashboardDisplayData from "./DashboardDisplayData";
  import DashboardRowActions from "@/components/Dashboard/DashboardRowActions";

  export default {
    name: 'dashboard-display-item',
    props: {
      pageTitle: String,
      typeLabel: String,
      displayItem: Object,
      id: String,
      itemLabel: String,
      apiErrors: Array,
      urlPrefix: String,
      dashboardFetchData: Function,
      refreshPath: String,
      deleteIcon: String,
      detailIcon: String,
      editIcon: String,
      refreshIcon: Boolean,
    },
    components: {
      DashboardDisplayData,
      DashboardRowActions,
    },
    data() {
      return {
        dashboardSearchQuery: '',
      };
    },
    methods: {
      refreshRequest() {
        this.$swal({
          title: this.$t('ui.modal.titles.on_it'),
          text: this.$t('ui.modal.messages.refreshing_data'),
          icon: 'success',
          showConfirmButton: false,
          timer: 1200
        });
        if (this.dashboardFetchData != null) {
          this.dashboardFetchData()
        } else if (this.refreshPath != null) {
          this.$store.dispatch(this.refreshPath);
        }
      },
    },
    watch: {
      dashboardSearchQuery(value) {
        let result = this.$parent.$parent.displayItem;
        this.$parent.$parent.dashboardSearchQuery = value;
        if (value !== '') {
          result = this.$parent.$parent.dashboardFuseSearch.search(value);
        }
        this.$parent.$parent.dashboardSearchedData = result;
      }
    }
  };
</script>

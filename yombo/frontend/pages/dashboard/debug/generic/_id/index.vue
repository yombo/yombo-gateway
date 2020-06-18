<template>
  <dashboard-display-index
    :pageTitle="$t('ui.navigation.debug') + ':' + $t('ui.navigation.' + debug_type)"
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
               small
               >
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
  import { ActionDetails } from '@/components/Dashboard/Actions';
  import { dashboardApiIndexMixin } from "@/mixins/dashboardApiIndexMixin";
  import Fuse from 'fuse.js'

  export default {
    layout: 'dashboard',
    mixins: [dashboardApiIndexMixin],
    components: {
      ActionDetails,
    },
    data: function() {
      return  {
        apiErrors: null,
        debug_type: this.$route.params.id,
      }
    },
    // computed: {
    //   tableColumns1: function () {
    //     if (this.dashboardDisplayItems.length == 0) {
    //       return []
    //     }
    //     let keys = Object.keys(this.dashboardDisplayItems[0]);
    //     let results = [];
    //     let that = this;
    //     keys.forEach(function (item, index) {
    //         results.push({key: item, label: that.$i18n.t(`ui.common.${item}`)})
    //     });
    //     return results
    //   },
    // },
    methods: {
      dashboardFetchData() {
        let that = this;
        try {
          window.$nuxt.$gwapiv1.debug().debug(this.debug_type)
            .then(response => {
              that.dashboardDisplayItems = [];
              response.data['data'].forEach(function (item, index) {
                that.dashboardDisplayItems.push(item["attributes"])
              });
              that.dashboardFuseSearch = new Fuse(that.dashboardDisplayItems)
            });
        } catch (ex) {  // Handle error
          console.log("pages/index: has an error");
          console.log(ex);
          return
        }
      }
    },
    beforeRouteUpdate (to, from, next) {
      this.debug_type = to.params.id;
      next();
    }
  };
</script>

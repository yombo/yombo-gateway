import { dashboardApiCoreMixin } from "@/mixins/dashboardApiCoreMixin.js";
import { Table, TableColumn, Select, Option } from 'element-ui';

import DashboardDisplayIndex from '@/components/Dashboard/DashboardDisplayIndex.vue';
import DashboardTable from '@/components/Dashboard/DashboardTable';
import DashboardTablePagination from '@/components/Dashboard/DashboardTablePagination.vue';

export const dashboardApiIndexMixin = {
  components: {
    [Select.name]: Select,
    [Option.name]: Option,
    [Table.name]: Table,
    [TableColumn.name]: TableColumn,
    DashboardDisplayIndex,
    DashboardTable,
    DashboardTablePagination,
  },
  mixins: [dashboardApiCoreMixin],
  data() {
    return {
      apiErrors: null,
      dashboardBusModel: null,
      dashboardFuseSearch: null,
      dashboardSearchQuery: '',
      dashboardSearchedData: [],
      dashboardDisplayItems: null,
      dashboardTablePage1: 1,  // Support multiple tabs
      dashboardTablePage2: 1,
      dashboardTablePage3: 1,
      dashboardTablePage4: 1,
      dashboardTablePage5: 1,

    };
  },
  computed: {
    dashboardQueriedData() {
      let result = this.dashboardDisplayItems;
      if (this.dashboardSearchQuery.length > 0) {
        result = this.dashboardSearchedData;
      }
      return result;
    },
    dashboardTableRowsPerPage: {
      get () {
        return this.$store.state.frontend.settings.dashboardTableRowsPerPage;
      },
      set (value) {
        this.$store.commit('frontend/settings/set', { dashboardTableRowsPerPage: value });
      }
    },
  },
  methods: {
    currentPageUpdated: function (attributes) {
      this[attributes['currentPageName']] = attributes['currentPage']
    },
    dashboardModelDataUpdated: function (changedIds) {
      this.dashboardGetFuseData();
      this.dashboardUpdateFuseSearch()
    },
    dashboardUpdateFuseSearch: function () {
      let result = this.dashboardDisplayItems;
      let value = this.dashboardSearchQuery;
      let threshold = null;
      if (value.length <= 2)
        threshold = 0.5;
      else if (value.length <= 3)
        threshold = 0.4;
      else
        threshold = 0.35;

      this.dashboardFuseSearch.options.threshold = threshold;
      if (value !== '') {
        // console.log(this.$parent);
        let tempResult = this.dashboardFuseSearch.search(value);
        result = [];
        for (let index = 0; index < tempResult.length; index++) {
          result.push(tempResult[index]['item']);
        }
      }
      this.dashboardSearchedData = result;
    },
    dashboardFetchData: function (forceFetch = true) {
      let that = this;
      this.apiErrors = null;
      let fetchType = "refresh";
      if (forceFetch)
        fetchType = "fetch";
      this.$store.dispatch(`gateway/${this.dashboardBusModel}/${fetchType}`)
        .then(function() {
          that.dashboardGetFuseData();
        })
        .catch(error => {
          that.apiErrors = this.$handleApiErrorResponse(error);
        });
    }
  },
  mounted() {
    window.$nuxt.$bus.$on(`store_gw_${this.dashboardBusModel}_updated`, e=> this.dashboardModelDataUpdated(e));
    window.$nuxt.$bus.$on('dashboardTable_currentPage', e=> this.currentPageUpdated(e));
  },
  watch: {
    dashboardSearchQuery(value) {
      this.dashboardUpdateFuseSearch();
    }
  }
};

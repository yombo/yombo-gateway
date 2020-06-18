<template>
  <div v-if="showPagination"
       :class="layoutClass"
    >
    <div class="p-1">
      <b-form-select style="width: 4.5em;"
           v-model="dashboardTableRowsPerPage"
           :options="possibleRowsPerPage"></b-form-select>
    </div>
    <div class="p-1">
      <b-pagination
          :size="displaySize"
          first-number
          last-number
          v-model="currentPage"
          :total-rows="rowCount"
          :per-page="dashboardTableRowsPerPage"
          :aria-controls="tableName"
        >
      </b-pagination>
    </div>
  </div>
</template>

<script>
  export default {
    name: 'dashboard-table-pagination',
    props: {
      rowCount: Number,
      tableName: String,
      tableIndex: String,
      position: String,
    },
    computed: {
      possibleRowsPerPage: function () {
        return this.$store.state.frontend.settings.dashboardPossibleRowsPerPage;
      },
      displaySize() {
        if (this.position == 'top') {
          return this.$store.state.frontend.settings.dashboardTableTopPaginationSize;
        }
        if (this.position == 'bottom') {
          return this.$store.state.frontend.settings.dashboardTableBottomPaginationSize;
        }
      },
      showPagination() {
        let configuredPosition = this.$store.state.frontend.settings.dashboardTablePaginationPosition;
        if (this.position == 'top' && (['top', 'both'].indexOf(configuredPosition) >= 0)) {
          return true;
        }
        else if (this.position == 'bottom' && (['bottom', 'both'].indexOf(configuredPosition) >= 0)) {
          return true;
        }
      },
      layoutClass() {
        if (this.position == 'top') {
          return `d-flex float-${this.$store.state.frontend.settings.dashboardTableTopPaginationAlign}`
        }
        if (this.position == 'bottom') {
          return `d-flex float-${this.$store.state.frontend.settings.dashboardTableBottomPaginationAlign}`
        }
      },
      currentPageName() {
        return `dashboardTablePage${this.tableIndex}`;
      },
      dashboardTableBottomPaginationSize() {
          return this.$store.state.frontend.settings.dashboardTableBottomPaginationSize;
      },
      dashboardTableRowsPerPage: {
        get () {
          return this.$store.state.frontend.settings.dashboardTableRowsPerPage;
        },
        set (value) {
          this.$store.commit('frontend/settings/set', { dashboardTableRowsPerPage: value });
        }
      },
      currentPage: {
        get () {
          return this.currentPageValue;
        },
        set (value) {
          this.currentPageValue = value;
          this.$bus.$emit('dashboardTable_currentPage',
          {currentPageName: this.currentPageName, currentPage: value}
          );
        }
      },
    },
    data() {
      return {
        currentPageValue: 1,
      }
    },
    methods: {
      currentPageUpdated: function (attributes) {
        if (this.currentPageName === attributes['currentPageName']) {
          this.currentPageValue = attributes['currentPage']
        }
      }
    },
    mounted() {
      window.$nuxt.$bus.$on('dashboardTable_currentPage', e=> this.currentPageUpdated(e));
    },
  };
</script>

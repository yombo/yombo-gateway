<template>
  <div>
    <b-table striped hover
        :id="tableId"
        :items="data"
        :per-page="dashboardTableRowsPerPage"
        :current-page="currentPage"
        :fields="fields"
        small
        >
      <slot></slot>
      <template v-for="field in fields">
        asdf
<!--        <slot :name="field.key" v-bind="data">aaa{{ data.item[field.key] }}</slot>-->
      </template>
    </b-table>
    <div class="d-flex">
      <div class="p-1">
        <b-form-select style="width: 4.5em;"
             v-model="dashboardTableRowsPerPage"
             :options="dashboardPossibleRowsPerPage"></b-form-select>
      </div>
      <div class="p-1">
        <b-pagination size="md"
          first-number
          last-number
          v-model="currentPage"
          :total-rows="data.length"
          :per-page="dashboardTableRowsPerPage"
          :aria-controls="tableId"
          align="right"
          >
        </b-pagination>
      </div>
    </div>
  </div>
</template>

<script>
  export default {
    name: 'dashboard-table',
    props: {
      data: Array,
      fields: Array,
    },
    computed: {
      dashboardPossibleRowsPerPage: function () {
        return this.$store.state.frontend.settings.dashboardPossibleRowsPerPage;
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
    data() {
      return {
        currentPage: 1,
        // tableId: 'asdfasdf',
        tableId: `dbtable${Math.floor(Math.random() * Math.floor(1000000))}`,
      }
    },
    mounted() {
      console.log(`dashboardTable....  fields: ${JSON.stringify(this.fields)}`);
      console.log(`dashboardTable....  slots:  ${JSON.stringify(this.slots)}`);

    },
    watch: {
      currentPage(value) {
        this.$bus.$emit('dashboardTable_currentPage',
          {currentPageName: this.currentPageName, currentPage: this.currentPage}
          );
      }
    }
  };
</script>

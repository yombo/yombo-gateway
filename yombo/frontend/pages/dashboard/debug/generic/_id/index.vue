<template>
  <div class="row">
    <div class="col-md-12">
      <card card-body-classes="table-full-width">
        <div slot="header">
          <h4 class="card-title">
            {{ $t('ui.navigation.debug') }}: {{ $t('ui.navigation.' + debug_type) }}
          </h4>
          <i v-on:click="getData" class="now-ui-icons arrows-1_refresh-69" style="color: #14375c;"></i>
          {{$t('ui.common.updated')}} {{display_age}}<br>
        </div>
        <div class="card-body">
          <el-table :data="items">
            <el-table-column :prop="col.prop" :label="col.prop" v-for="col in columns" :key="col.prop" sortable>
            </el-table-column>
          </el-table>
        </div>
      </card>
    </div>

  </div>
</template>
<script>
import { ActionDetails } from '@/components/Dashboard/Actions';
import humanizeDuration from "humanize-duration";
import { Table, TableColumn } from 'element-ui';

export default {
  layout: 'dashboard',
  components: {
    [Table.name]: Table,
    [TableColumn.name]: TableColumn,
    ActionDetails,
  },
  data: function() {
    return  {
      debug_type: this.$route.params.id,
      items: [],
      downloaded_at: 0,
      display_age: "Unknown age",
    }
  },
  computed: {
    columns: function () {
      // console.log(this.items);
      if (this.items.length == 0) {
        return []
      }
      let keys = Object.keys(this.items[0]);
      let results = [];
      keys.forEach(function (item, index) {
          results.push({prop: item})
      });
      return results
    },
  },
  methods: {
    updateDataAge() {
      if (this.display_age <= 1) {
        this.display_age = "Unknown age"
      } else {
        this.display_age = humanizeDuration(Date.now() - this.downloaded_at, {
          language: this.$i18n.locale,
          round: true
        }) + " ago";
      }
    },
    getData() {
      try {
        window.$nuxt.$gwapiv1.debug().debug(this.debug_type)
          .then(response => {
              let results = [];
              response.data['data'].forEach(function (item, index) {
                results.push(item["attributes"])
              });
              this.items = results;
              this.downloaded_at = Number(Date.now());
              this.updateDataAge();
          });
      } catch (ex) {  // Handle error
        console.log("pages/index: has an error");
        console.log(ex);
        return
      }
    }
  },
  mounted () {
    this.getData(this.$route.params.id);
    this.$options.interval = setInterval(this.updateDataAge, 5000);
  },
  beforeDestroy () {
    clearInterval(this.$options.interval);
  },
  beforeRouteUpdate (to, from, next) {
    this.debug_type = to.params.id
    this.getData();
    next();
  }
};

</script>
<style scoped>
.table-transparent {
  background-color: transparent !important;
}
</style>

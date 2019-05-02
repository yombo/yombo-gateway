<template>
  <div class="row">
    <div class="col-md-12">
      <card card-body-classes="table-full-width">
        <div slot="header">
        <h4 class="card-title">
           {{ $t('ui.navigation.atoms') }}
         </h4>
          <div class="fa-pull-right">
           <el-input
                  class="fa-pull-right"
                  v-model="search"
                  size="mini"
                  :placeholder="$t('ui.label.search_ddd')"/>
          </div>
           <div slot="footer" class="stats">
             <i v-on:click="refreshRequest" class="now-ui-icons arrows-1_refresh-69" style="color: #14375c;"></i>
             {{$t('ui.label.updated')}} {{display_age}}
           </div>
        </div>
        <div class="card-body">
          <el-table
             :data="atoms.filter(data => !search
             || data.id.toLowerCase().includes(search.toLowerCase())
             || data.gateway_id.toLowerCase().includes(search.toLowerCase())
             || data.source.toLowerCase().includes(search.toLowerCase())
             // || data.value_human.toLowerCase().includes(search.toLowerCase())
             )"
          >
            <el-table-column :label="$t('ui.label.atom')" property="id"></el-table-column>
            <el-table-column :label="$t('ui.label.gateway')" property="gateway_id"></el-table-column>
            <el-table-column :label="$t('ui.label.value')" property="value_human"></el-table-column>
            <el-table-column :label="$t('ui.label.source')" property="source"></el-table-column>
            <el-table-column :label="$t('ui.label.created_at')" property="created_at"></el-table-column>
            <el-table-column :label="$t('ui.label.updated_at')" property="updated_at"></el-table-column>
          </el-table>
        </div>
      </card>
    </div>

  </div>
</template>
<script>
import { Table, TableColumn } from 'element-ui';

export default {
  layout: 'dashboard',
  components: {
    [Table.name]: Table,
    [TableColumn.name]: TableColumn
  },
  data() {
    return {
      search: '',
      display_age: '0 seconds',
    };
  },
  computed: {
    atoms () {
      let source = this.$store.state.gateway.atoms.data;
      let results = [];
      let cache = {}
      let atom = {}
      let gateway_label = ""
      let gateawy = null

      Object.keys(source).forEach(key => {
        results.push(source[key]);
      });
      return results
    },
  },

  methods: {
    refreshRequest() {
      this.$swal({
          title: this.$t('ui.modal.titles.on_it'),
          text: this.$t('ui.modal.mesages.refreshing_data'),
          type: 'success',
          showConfirmButton: true,
          timer: 1000
      });
      this.$store.dispatch('gateway/atoms/fetch');
    },
    updateDisplayAge () { // called by setInterval setup in mounted()
      this.display_age =  this.$store.getters['gateway/atoms/display_age'](this.$i18n.locale);
    },
    device_updated(updated_at) { // called by bus.$on setup in mounted()
      this.updateDisplayAge();
      console.log("Devices were updated: " + updated_at);
    }

  },
  mounted () {
    this.updateDisplayAge();
    this.$options.interval = setInterval(this.updateDisplayAge, 1000);
    this.$store.dispatch('yombo/gateways/refresh');
    this.$store.dispatch('gateway/atoms/refresh');
  },
  beforeDestroy () {
    clearInterval(this.$options.interval);
  },
};
</script>

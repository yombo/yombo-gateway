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
          <last-updated refresh="gateway/atoms/fetch" getter="gateway/atoms/display_age"/>
        </div>
        <div class="card-body">
          <el-table
             :data="items.filter(data => !search
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
import LastUpdated from '@/components/Dashboard/LastUpdated.vue'

import { Table, TableColumn } from 'element-ui';

export default {
  layout: 'dashboard',
  components: {
    [Table.name]: Table,
    [TableColumn.name]: TableColumn,
    LastUpdated,
  },
  data() {
    return {
      search: '',
    };
  },
  computed: {
    items () {
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
  mounted () {
    this.$store.dispatch('gateway/atoms/refresh');
  },
};
</script>

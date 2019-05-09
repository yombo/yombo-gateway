<template>
  <div class="row">
    <div class="col-md-12">
      <card card-body-classes="table-full-width">
        <div slot="header">
          <div class="fa-pull-right">
            <nuxt-link class="navbar-brand fa-pull-right" :to="localePath('dashboard-locations-add')">
              <button type="button" class="btn btn-info btn-sm" data-dismiss="modal">
                <i class="fas fa-plus-circle fa-pull-left" style="font-size: 1.5em;"></i> &nbsp; Add new</a>
                </button>
            </nuxt-link>
            <br>
            <el-input
                  class="fa-pull-right"
                  v-model="search"
                  size="mini"
                  :placeholder="$t('ui.label.search_ddd')"/>
          </div>
          <h4 class="card-title">
           {{ $t('ui.navigation.locations') }}
          </h4>
          <last-updated refresh="yombo/locations/fetch" getter="yombo/locations/display_age"/>
        </div>
        <div class="card-body">
          <el-table
            :data="items.filter(data => !search
             || data.label.toLowerCase().includes(search.toLowerCase())
             || data.description.toLowerCase().includes(search.toLowerCase())
             )"
          >
            <el-table-column :label="$t('ui.label.label')" property="label"></el-table-column>
            <el-table-column :label="$t('ui.label.description')" property="description"></el-table-column>
            <el-table-column
              align="right" :label="$t('ui.label.actions')">
              <div slot-scope="props" class="table-actions">
                <action-details path="dashboard-locations-details" :id="props.row.id"/>
                <action-edit path="dashboard-locations-edit" :id="props.row.id"/>
                <action-delete path="dashboard-locations-delete" :id="props.row.id"
                               i18n="location" :item_label="props.label"/>
              </div>
            </el-table-column>
          </el-table>
        </div>
      </card>
    </div>

  </div>
</template>

<script>
import { ActionDelete, ActionDetails, ActionEdit } from '@/components/Dashboard/Actions';
import LastUpdated from '@/components/Dashboard/LastUpdated.vue'

import { Table, TableColumn } from 'element-ui';

import Location from '@/models/location'

export default {
  layout: 'dashboard',
  components: {
    ActionEdit,
    [Table.name]: Table,
    [TableColumn.name]: TableColumn,
    ActionDelete,
    ActionDetails,
    ActionEdit,
    LastUpdated,
  },
  data() {
    return {
      search: '',
    };
  },
  computed: {
    items () {
      return Location.query().where('location_type', 'location').orderBy('label', 'desc').get()
    },
  },
  mounted () {
    this.$store.dispatch('yombo/locations/refresh');
  },
};
</script>

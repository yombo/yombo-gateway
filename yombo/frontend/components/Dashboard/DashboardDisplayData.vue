<template>
  <span>
    <div v-if="displayItem === null && apiErrors === null">
      <dashboard-data-loading></dashboard-data-loading>
    </div>
    <div v-else-if="apiErrors !== null">
      <p>
        <button type="button" class="btn btn-info btn-sm" data-dismiss="modal"
        v-on:click="refreshRequest">
          <i class="fas fa-sync-alt fa-pull-left" style="font-size: 1.5em;"></i> &nbsp; {{ $t("ui.common.retry") }}
        </button>
      </p>
      {{ $t("ui.api_code.common.error_with_data_request") }}:
      <li v-for="error in apiErrors">
        <em>{{ $t(`ui.api_code.${error.code}.short`) }}</em>
        <ul>
          <li>{{ error.detail }}</li>
          <li>{{ $t("ui.api_code.common.additional_details")}}: {{ $t(`ui.api_code.${error.code}.long`) }}</li>
        </ul>
      </li>
    </div>
    <div v-else><slot></slot></div>
  </span>
</template>

<script>
  import DashboardDataLoading from '@/components/Dashboard/DashboardDataLoading.vue';

  export default {
    name: 'dashboard-display-data',
    components: {
      DashboardDataLoading,
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
        this.$parent.$parent.dashboardFetchData()
      }
    },
    props: ['displayItem', 'apiErrors'],
  };
</script>

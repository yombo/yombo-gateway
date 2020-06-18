<template>
  <span>
    <div v-if="deviceTypes.length == 0 && apiErrors === null">
      <dashboard-data-loading></dashboard-data-loading>
    </div>
    <div v-else-if="apiErrors !== null">
      {{ $t("ui.api_code.common.error_with_data_request") }}:
      <li v-for="error in apiErrors">
        <em>{{ $t(`ui.api_code.${error.code}.short`) }}</em>
        <ul>
          <li>{{ error.detail }}</li>
          <li>{{ $t("ui.api_code.common.additional_details")}}: {{ $t(`ui.api_code.${error.code}.long`) }}</li>
        </ul>
      </li>
    </div>
    <div v-else>
      <div class="row">
        <div class="col-md-12">
          <card class="card-chart" no-footer-line>
            <div slot="header">
              <h2 class="card-title">
                {{ $t('ui.label.add_device') }} - Step: 1 of 2
              </h2>
            </div>
            <p>
              This new device wizard will get your new device up and running quickly.
            </p>
            <p>
              Select a device type to add:
            </p>
            <form @submit.prevent>
            <p>
              <form @submit.prevent="handleSubmit">
                <multiselect v-model="deviceTypeSelected" track-by="id" label="label"
                             :options="deviceTypes" :searchable="true"
                             :max-height="1000"
                             placeholder="Select a device type"></multiselect>
                 <button class="btn btn-outline-warning btn-success"
                         type="submit"
                         :disabled="deviceTypeSelected == ''">
                   {{ $t('ui.label.add_device') }}<i class="far fa-paper-plane ml-2"></i>
                 </button>
              </form>
            </p>
            </form>
          </card>
        </div>
      </div>
    </div>
  </span>
</template>

<script>
  import Multiselect from 'vue-multiselect'

  import { dashboardApiCoreMixin } from "@/mixins/dashboardApiCoreMixin";
  import DashboardDataLoading from '@/components/Dashboard/DashboardDataLoading.vue';

  import { GW_Device_Type } from '@/models/device_type'
  import Fuse from 'fuse.js'

  export default {
    layout: 'dashboard',
    components: {
      DashboardDataLoading,
      Multiselect
    },
    mixins: [dashboardApiCoreMixin],
    data() {
      return {
        metaPageTitle: this.$t('ui.navigation.lock'),
        apiErrors: null,
        deviceTypes: [],
        deviceTypeSelected: '',
      };
    },
    methods: {
      handleSubmit() {
        console.log(this.deviceTypeSelected.id);
        this.$router.push(
          window.$nuxt.localePath({name: 'dashboard-devices-add-id', params: {id: this.deviceTypeSelected.id} })
        );
      },
      dashboardFetchData(forceFetch = true) {
        let that = this;
        this.apiErrors = null;
        let fetchType = "refresh";
        if (forceFetch)
          fetchType = "fetch";
        this.$store.dispatch(`gateway/device_types/${fetchType}`)
          .then(function() {
            that.deviceTypes = [];
            let deviceTypes = GW_Device_Type.query()
                                            .orderBy('label', 'asc')
                                            .where('is_usable', true)
                                            .get();

            let arrayLength = deviceTypes.length;
            for (let i = 0; i < arrayLength; i++) {
              if (deviceTypes[i].machine_label == "device") {
                continue;
              }
              that.deviceTypes.push(deviceTypes[i]);
            }
          })
          .catch(error => {
            that.apiErrors = this.$handleApiErrorResponse(error);
          });
      }
    },
    mounted() {
      this.$store.dispatch(`gateway/locations/refresh`);
    }
  };
</script>
<style scoped>
  element.style {
    margin-bottom: 0px !important;
    margin-right: 0px !important;
  }
    .el-input__inner {
      @extend .btn-round, .btn-info;
    }

</style>

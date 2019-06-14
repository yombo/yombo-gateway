<template>
  <div class="row">
    <div class="col-md-12">
        <card class="card-chart" no-footer-line>
          <div slot="header">
            <h2 class="card-title">
              {{ $t('ui.label.add_device') }}
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
             <b-form-select :options="devices_types"></b-form-select>
             <button class="btn btn-outline-warning btn-info" type="submit">{{ $t('ui.label.add_device') }}<i class="far fa-paper-plane ml-2"></i></button>
          </p>
          </form>
        </card>
    </div>
  </div>
</template>
<script>

import Device_Type from '@/models/device_type'

import { Select, Option } from 'element-ui';

export default {
  layout: 'dashboard',
  components: {
    [Option.name]: Option,
    [Select.name]: Select,
  },
  computed: {
    devices_types () {
      var results = [];
      var device_tyes = Device_Type.query().orderBy('label').get();
      var arrayLength = device_tyes.length;
      for (var i = 0; i < arrayLength; i++) {
        results.push({value: device_tyes[i].id, text: device_tyes[i].label});
      }
      return results;
    },
  },

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

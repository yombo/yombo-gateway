<template>
  <card class="card-chart" no-footer-line>
  <div slot="header">
    <h3 class="card-title">
      Gateway info
    </h3>
  </div>
  <ul style="padding: 0 15px;">
    <li>Label: <strong>{{ systemInfo.label }}</strong></li>
    <li>Description: <strong>{{ systemInfo.description }}</strong></li>
    <li>DNS Name: <strong>{{ systemInfo.dns_name }}</strong></li>
    <li>Is Master: <strong>{{ systemInfo.is_master }}</strong></li>
    <li>Version: <strong>{{ systemInfo.version }}</strong></li>
    <li>Running Since: <strong>{{ systemInfo.running_since | epoch_to_datetime_terse}}</strong></li>
  </ul>
</card>
</template>

<script>
  export default {
    computed: {
      pageTitle: function () {
        return this.gwLabel + " Home";
      },
      systemInfo: function () {
        return this.$store.state.gateway.systeminfo;
      },
    },
    created: function () {
      this.$store.dispatch('gateway/systeminfo/refresh');
    },
}
</script>

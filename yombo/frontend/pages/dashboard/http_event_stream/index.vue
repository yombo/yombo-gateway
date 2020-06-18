<template>
  <div class="row">
    <div class="col-md-12">
        <card class="card-chart" no-footer-line>
          <div slot="header">
            <h2 class="card-title">
              HTTP Event Stream
            </h2>
          </div>
          <p>
            HTTP Events will connect to the gateway and listen for broadcasts, this can be used as a backup
            for a stable MQTT connection.
          </p>
          <p>Content has not been created, this is a simple placeholder.</p>
          <p>
            Content sources:
          </p>
          <ul>
            <li>Logic: </li>
            <li>Display: </li>
          </ul>
        </card>
    </div>

  </div>
</template>
<script>

export default {
  layout: 'dashboard',
};
</script>
<style scoped>
.table-transparent {
  background-color: transparent !important;
}
</style>

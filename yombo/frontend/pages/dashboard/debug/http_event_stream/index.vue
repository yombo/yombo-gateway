<template>
  <div class="row">
    <div class="col-md-12">
        <card class="card-chart" no-footer-line>
          <div slot="header">
            <h2 class="card-title">
              Debug: Cache
            </h2>
          </div>
          <p>Content has not been created, this is a simple placeholder.</p>
          <p><strong>Debug pages will be the last to be implemented, or unless they are needed
            for frontend application development.</strong></p>
          <p>
            Content sources:
          </p>
          <ul>
            <li>Logic: yombo-gateway/yombo/lib/webinterface/routes_old/debug.py</li>
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

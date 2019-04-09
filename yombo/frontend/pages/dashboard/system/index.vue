<template>
  <div class="row">
    <div class="col-md-12">
        <card class="card-chart" no-footer-line>
          <div slot="header">
            <h2 class="card-title">
              System Settings
            </h2>
          </div>
          <p>Content has not been created, this is a simple placeholder.</p>
          <p>
            Content sources:
          </p>
          <ul>
            <li><nuxt-link to="/dashboard/system/overview" class="nav-link">Overview</nuxt-link></li>
            <li><nuxt-link to="/dashboard/system/debug" class="nav-link">Debug</nuxt-link></li>
            <li><nuxt-link to="/dashboard/system/events" class="nav-link">Events</nuxt-link></li>
            <li><nuxt-link to="/dashboard/system/http_event_stream" class="nav-link">HTTP Event Stream</nuxt-link></li>
            <li><nuxt-link to="/dashboard/system/status" class="nav-link">Status</nuxt-link></li>
            <li><nuxt-link to="/dashboard/system/web_logs" class="nav-link">Web Logs</nuxt-link></li>
            <li><nuxt-link to="/dashboard/system/debug" class="nav-link">Debug</nuxt-link></li>
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

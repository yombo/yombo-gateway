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
          <ul>
            <li><nuxt-link to="/dashboard/settings/dns" class="nav-link">Settings - DNS</nuxt-link></li>
            <li><nuxt-link to="/dashboard/settings/encryption" class="nav-link">Settings - Encryption</nuxt-link></li>
            <li><nuxt-link to="/dashboard/settings/gateways" class="nav-link">Settings - Gateways</nuxt-link></li>
            <li><nuxt-link to="/dashboard/settings/locations" class="nav-link">Settings - Locations</nuxt-link></li>
            <li><nuxt-link to="/dashboard/settings/yomboini" class="nav-link">Settings - Yombo.Ini</nuxt-link></li>
            <li><nuxt-link to="/dashboard/settings/dns" class="nav-link">Settings - DNS</nuxt-link></li>
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

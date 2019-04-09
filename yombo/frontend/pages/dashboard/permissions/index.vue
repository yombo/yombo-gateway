<template>
  <div class="row">
    <div class="col-md-12">
        <card class="card-chart" no-footer-line>
          <div slot="header">
            <h2 class="card-title">
              Permissions
            </h2>
          </div>
          <p>Manage gateway permissions.</p>
          <ul>
            <li><nuxt-link to="/dashboard/permissions/roles" class="nav-link">Roles</nuxt-link></li>
            <li><nuxt-link to="/dashboard/permissions/users" class="nav-link">Users</nuxt-link></li>
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

<template>
  <card class="card-chart" no-footer-line>
    <div slot="header">
      <h2 class="card-title">
        Frontend layout examples
      </h2>
    </div>
    <p>Examples of layouts that can be templates for various things.</p>
    <ul>
      <li><nuxt-link :to="localePath('dashboard-examples-cards')">Cards</nuxt-link></li>
    </ul>
  </card>
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

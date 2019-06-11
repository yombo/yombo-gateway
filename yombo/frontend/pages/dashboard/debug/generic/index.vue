<template>
  <div class="row">
    <div class="col-md-12">
      <card card-body-classes="table-full-width">
        <div slot="header">
          <h4 class="card-title">
            {{ $t('ui.navigation.debug') }}: {{ $t('ui.navigation.home') }}
          </h4>
        </div>
        <div class="card-body">
          Generic index.....
        </div>
      </card>
    </div>

  </div>
</template>
<script>

export default {
  layout: 'dashboard',
  components: {
  },
  mounted () {
  },
};

</script>
<style scoped>
.table-transparent {
  background-color: transparent !important;
}
</style>

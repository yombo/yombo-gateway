<template>
  <div class="row">
    <div class="col-md-12">
        <card class="card-chart" no-footer-line>
          <div slot="header">
            <h2 class="card-title">
              Global Items
            </h2>
          </div>
          <p>
            All Yombo items such as commands, modules, and device types can be managed from here.
          </p>
          <p>
            This allows you to manage private items for you account as well as contribute new items for public
            use.
          </p>
        </card>
    </div>

  </div>
</template>
<script>

export default {
  layout: 'globalitems',
};
</script>
<style scoped>
.table-transparent {
  background-color: transparent !important;
}
</style>

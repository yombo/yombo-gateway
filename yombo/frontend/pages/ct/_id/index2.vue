<template>
  <div class="row">
    <div class="col-md-12">
      control tower id -  {{ page_id }}
    </div>
  </div>
</template>

<script>

export default {
  layout: 'controltower',
  data() {
    return {
      page_id: this.$route.params.id,
    };
  },
  // computed: {
  //   item () {
  //     return Device.query().where('id', this.id).first()
  //   },
  // },
  // methods: {
  //   location: function(id) {
  //     return Location.query().where('id', id).first();
  //   }
  // },
  // mounted () {
  //   this.$bus.$emit("listenerUpdateBreadcrumb",
  //     {index: 2, path: "dashboard-devices-id-details", props: {id: this.id}, text: this.item.label});
  //   this.$bus.$emit("listenerDeleteBreadcrumb", 3);
  //   this.$store.dispatch('yombo/devices/refresh');
  //   this.$store.dispatch('yombo/locations/refresh');
  //   this.gateway = Gateway.query().where('id', this.item.gateway_id).first()
  // },
};
</script>

<template>
  <span>
    {{role_id | showline}}
  </span>
</template>

<script>

import { GW_Role } from '@/models/role'

export default {
  name: 'role-line',
  props: {
    role_id: String,
  },
  filters: {
    showline: function (value) {
      // console.log("Starting to find role...");
      let role = GW_Role.query().where('id', value).first();
      // console.log("role line:");
      // console.log(role);
      if (role === null) {
        return value;
      }
      return `${role.label} (${role.machine_label})`;
    }
  }
  // mounted() {
  //   this.updateDataAge();
  //   this.$options.interval = setInterval(this.updateDataAge, 1000);
  // },
  // beforeDestroy () {
  //   clearInterval(this.$options.interval);
  // },

};
</script>

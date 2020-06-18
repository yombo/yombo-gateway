<template>
  <div>
    Need a control tower ID, redirecting...
  </div>
</template>
<script>
export default {
    mounted () {
      this.$router.push(this.localePath('controltower'));
    }
}
</script>

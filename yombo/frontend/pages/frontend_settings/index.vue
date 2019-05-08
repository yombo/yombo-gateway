
<template>
  <section class="container">
    <div class="row">
      <div class="col-md-10 mx-auto">
          <card class="card-chart" no-footer-line>
            <div slot="header">
              <h2 class="card-title">
                Frontend Settings
              </h2>
              <p class="subheading" style="margin-bottom: .5em;">Various app settings</p>
            </div>
            <p>
              Settings for currently logged in user for <strong>this browser.</strong>. Changes here will only affect
              this browser for the current user.
            </p>
            <p>
              Form items here:
            </p>
            <ul>
              <li>Lock screen pin: (input form)</li>
            </ul>
          </card>
      </div>
    </div>
  </section>
</template>

<script>
export default {
    head() {
        return {
            title: 'Frontend Settings',
        }
    },
    data () {
          return {
              gwLabel: null
          }
      },
    computed: {
      pageTitle: function () {
        return this.gwLabel + " Home";
      },
      systemInfo: function () {
        return this.$store.state.systeminfo;
      },
      randomBGNumber : function(){
        return Math.floor(Math.random() * (10 - 1 + 1)) + 1;
      }
    },
    created: function () {
      if (this.gwLabel == null) {
        this.$store.dispatch('systeminfo/fetch');
      }
    },
}
</script>

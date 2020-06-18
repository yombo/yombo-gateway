<template>
  <section class="container">
    <portal to="topnavbar">
      {{ metaPageTitle }}1
    </portal>
    <div class="row justify-content-center">
      <div class="col-sm-12">
          <card class="card-chart center-block" no-footer-line>
            <div slot="header">
              <h2 class="card-title">
                {{ $t('ui.navigation.control_tower') }}
              </h2>
              <p class="subheading" style="margin-bottom: .5em;">Device Control</p>
            </div>
            <p>
              The control tower is used to view and control device states and is organized into pages.
              Select a start page below to start a control tower page.
            </p>
            <h5>Select a page to jump to:</h5>
              <form @submit.prevent="handleSubmit">
                <b-form-select v-model="selectedPage" :options="controlPanels" :select-size="9"></b-form-select>
                <button class="btn btn-outline-warning btn-info" type="submit" :disabled="selectedPage == ''">
                  {{ $t('ui.label.select') }}<i class="far fa-paper-plane ml-2"></i>
                </button>
              </form>
          </card>
      </div>
    </div>
  </section>
</template>

<script>
  export default {
    data () {
      return {
        metaPageTitle: this.$t('ui.navigation.control_tower'), // set within commonMixin
        selectedPage: "",
        controlPanels: [
        {
          value: 'ybobi__by_location',
          text: 'By Location'
        },
        {
          value: 'ybobi__by_type',
          text: 'By Type'
        },
        {
          value: 'xxxxxxxxxxxxxxxxxxxxxxxx',
          text: '──────────',
          disabled: true
        },
        {
          value: 'Option3',
          text: 'Option3'
        },
        {
          value: 'Option4',
          text: 'Option4'
        },
        {
          value: 'Option5',
          text: 'Option5'
        }],
      }
    },
    methods: {
      handleSubmit() {
        if (this.selectedPage.startsWith("ybobi__")) {
          let page_id = this.selectedPage.substring(7);
          this.$router.push(window.$nuxt.localePath({ name: `controltower-${page_id}` }));
          return
        }
        this.$router.push(window.$nuxt.localePath({name: 'ct-id', params: {id: this.selectedPage} }));
      }
    }
  }
</script>

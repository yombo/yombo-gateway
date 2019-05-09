<template>
  <div class="row">
    <div class="col-md-12">
        <card class="card-chart" no-footer-line>
          <div slot="header">
            <h2 class="card-title">
              {{ $t('ui.label.add_area') }}
            </h2>
          </div>
          <p>
            Create a new area.
          </p>
          <p>
            <b-container fluid>
              <b-row>
                <b-col class="my-auto" sm="4" md="3" lg="2">
                  <label for="label">{{$t('ui.label.label')}}:</label>
                </b-col>
                <b-col sm="8" md="9" lg="10">
                  <b-form-input id="label" placeholder="Label: House, Shed, Garage, Pool House"></b-form-input>
                </b-col>
              </b-row>
              <b-row>
                <b-col class="my-auto" sm="4" md="3" lg="2">
                  <label for="machine_label">{{$t('ui.label.machine_label')}}:</label>
                </b-col>
                <b-col sm="8" md="9" lg="10">
                      <b-form-input id="machine_label" placeholder="Machine Label: house, shed, garage, pool_house"></b-form-input>
                </b-col>
              </b-row>
              <b-row>
                <b-col class="my-auto" sm="4" md="3" lg="2">
                  <label for="description">{{$t('ui.label.description')}}:
                    <i class="fas fa-question-circle align-right" style="font-size: .9em; color: #2a5586;"></i></label>
                </b-col>
                <b-col sm="8" md="9" lg="10">
                      <b-form-input id="description" placeholder="Description"></b-form-input>
                </b-col>
              </b-row>
            </b-container>
            <button class="btn btn-outline-warning btn-info" type="submit">{{ $t('ui.label.add_area') }}
              <i class="fas fa-plus-circle fa-pull-right" style="font-size: 1.5em;"></i></button>
          </p>
        </card>
    </div>
  </div>
</template>
<script>

export default {
  layout: 'dashboard',
  components: {
  },
  computed: {
  },

};
</script>
<style scoped>
  .card label {
    color: #000000;
  }
  .row {
    margin-bottom: 5px;
  }
  element.style {
    margin-bottom: 0px !important;
    margin-right: 0px !important;
  }
    .el-input__inner {
      @extend .btn-round, .btn-info;
    }

</style>

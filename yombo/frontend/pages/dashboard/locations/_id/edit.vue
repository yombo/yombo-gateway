<template>
  <div>
    <card card-body-classes="table-full-width">
      <div slot="header">
      <h4 class="card-title">
         {{ $t('ui.common.edit') }} {{ $t('ui.common.state') }}: {{id}}
        <div class="pull-left">
          <nuxt-link :to="'/dashboard/devices/'+id+'/details'">
            <i class="fas fa-chevron-left"></i>
          </nuxt-link> &nbsp;
        </div>
       </h4>
      </div>
      <p></p>
      <div v-if="item === null"><spinner></spinner></div>
      <div class="card-body" v-else>
        <b-form @submit="onSubmit" @reset="onReset">
          <b-form-group>
            Value@:
            <b-button v-b-modal.value variant="neutral" size="help"><i class="fas fa-question" style="font-size: 1.5em;"></i></b-button>
            <b-form-input v-model="item.value" required placeholder="Device label"></b-form-input>
          </b-form-group>
            <b-form-group>
              Value Type:
              <b-button v-b-modal.value_type variant="neutral" size="help"><i class="fas fa-question" style="font-size: 1.5em;"></i></b-button>
                <b-form-select v-model="item.value_type" label="Status:">
                  <b-form-select-option value="boolean">Boolean</b-form-select-option>
                  <b-form-select-option value="epoch">Epoch (time in seconds)</b-form-select-option>
                  <b-form-select-option value="float">Float</b-form-select-option>
                  <b-form-select-option value="int">Integer</b-form-select-option>
                  <b-form-select-option value="string">String</b-form-select-option>
                </b-form-select>
            </b-form-group>
          <b-button type="reset" variant="danger">Reset</b-button>
          <b-button type="submit" variant="success" class="pull-right">Submit</b-button>
        </b-form>
        <b-card class="mt-3" header="Form Data Result">
          <pre class="m-0">{{ item }}</pre>
        </b-card>
      </div>
    </card>

    <b-modal id="value" title="Value" ok-only>
      <p>
        The value to set.
      </p>
    </b-modal>
    <b-modal id="value_type" title="Value Type" ok-only>
      <p>
        Used to convert the value into a displayable value.
      </p>
    </b-modal>
  </div>
</template>
<script>
  // import VSelect from "@alfsnd/vue-bootstrap-select";
  import Spinner from '@/components/Dashboard/Spinner.vue';

  import { GW_Atom } from '@/models/atom'

  export default {
    layout: 'dashboard',
    components: {
      Spinner,
    },
    data() {
      return {
        id: this.$route.params.id,
        item: null,
      };
    },
    computed: {
      systemInfo: function () {
        return this.$store.state.gateway.systeminfo;
      },
    },
    watch: {

    },
    methods: {
      onSubmit(evt) {
          evt.preventDefault();
          alert(JSON.stringify(this.item));
        },
      onReset(evt = null) {
          evt.preventDefault();
          this.item = GW_Atom.query().where('id', this.id).first();
        },
      convertToSelect(locations, text_field = "label") {
        let results = [];
        let location = null;
        for (let index = 0; index < locations.length; index++) {
          location = locations[index];
          results.push({
            value: location.id,
            text: location[text_field],
          });
        }
        return results;
      },
    },
    beforeMount: function beforeMount() {
      let that = this;
      this.$store.dispatch('gateway/atoms/fetchOne', this.id)
        .then(function() {
          that.item = GW_Atom.query().where('id', that.id).first();
          that.$bus.$emit("listenerUpdateBreadcrumb",
            {index: 2, path: "dashboard-atoms-id-details", props: {id: that.id}, text: that.id});
          that.$bus.$emit("listenerDeleteBreadcrumb", 3);
          that.$bus.$emit("listenerAppendBreadcrumb",
            {index: 2, path: "dashboard-atoms-id-details", props: {id: that.id}, text: "ui.navigation.details"});
        })
        .catch(error => {
          console.log(error.response)
        });
    },
  };
</script>

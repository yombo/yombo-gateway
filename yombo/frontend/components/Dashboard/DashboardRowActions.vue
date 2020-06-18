<template>
  <span>
    <n-button v-if="refreshIcon" @click.native="handleReload()"
              class="edit"
              type="info"
              size="sm" round icon>
      <i class="fas fa-sync-alt"></i>
    </n-button>
    <n-button v-if="detailIcon" @click.native="handleDetails()"
              class="edit"
              type="info"
              size="sm" round icon>
      <i class="fa fa-receipt"></i>
    </n-button>
    <n-button v-if="editIcon" @click.native="handleEdit()"
              class="edit"
              type="info"
              size="sm" round icon>
      <i class="fa fa-edit"></i>
    </n-button>
    <n-button v-if="disableIcon && displayItem.status == 1" @click.native="handleDisable()"
              class="enable"
              type="success"
              size="sm" round icon>
      <i class="fa fa-power-off"></i>
    </n-button>
    <n-button v-if="enableIcon && displayItem.status == 0" @click.native="handleDisable()"
              class="enable"
              type="success"
              size="sm" round icon>
      <i class="fa fa-power-off"></i>
    </n-button>
    <n-button v-if="deleteIcon" @click.native="handleDelete()"
              class="remove"
              type="danger"
              size="sm" round icon>
      <i class="fa fa-times"></i>
    </n-button>
  </span>
</template>

<script>
import DashboardDataLastUpdated from "./DashboardDataLastUpdated";

export default {
  name: 'dashboard-index-row-actions',
  components: {
    DashboardDataLastUpdated,
  },
  props: {
    typeLabel: String,
    displayItem: Object,
    id: String,
    itemLabel: String,
    deleteIcon: String,
    detailIcon: String,
    disableIcon: String,
    editIcon: String,
    enableIcon: String,
    dashboardFetchData: Function,
    refreshIcon: Boolean,
  },
  data() {
    return {
      dashboardSearchQuery: '',
    };
  },
  methods: {
    handleDelete() {
      this.$swal({
        title: `${this.$t('ui.common.delete')} ${this.typeLabel.toLowerCase()}? <br> ${this.itemLabel}`,
        text: this.$t('ui.phrase.cannot_undo'),
        icon: 'warning',
        showCancelButton: true,
        confirmButtonClass: 'btn btn-success btn-fill',
        cancelButtonClass: 'btn btn-danger btn-fill',
        confirmButtonText: 'Yes, delete it!',
        buttonsStyling: false
      }).then(result => {
        if (result.value) {
          console.log(`Calling dispatch: ${this.deleteIcon}`);
          this.$store.dispatch(this.deleteIcon, this.id)
            .then(function() {
              this.$swal({
                title: this.$t('ui.common.deleted'),
                text: `${this.$t('ui.common.deleted')} ${this.typeLabel.toLowerCase()}: ${this.itemLabel}`,
                icon: 'success',
                confirmButtonClass: 'btn btn-success btn-fill',
                buttonsStyling: false
              });
            })
            .catch(error => {
              console.log(`handle delete, API error: ${error}`);
              console.log(error.code);
              console.log(error.message);
          });
        }
      });
    },
    handleDetails() {
      this.$router.push(this.localePath({name:this.detailIcon, params: {id: this.id}}));
    },
    handleDisable() {
      this.$swal({
        title: `${this.$t('ui.common.disable')} ${this.typeLabel.toLowerCase()}? <br> ${this.itemLabel}`,
        text: this.$t('ui.phrase.gateway_maybe_need_rebooted_after_change'),
        icon: 'warning',
        showCancelButton: true,
        confirmButtonClass: 'btn btn-success btn-fill',
        cancelButtonClass: 'btn btn-danger btn-fill',
        confirmButtonText: 'Yes, disable it!',
        buttonsStyling: false
      }).then(result => {
        if (result.value) {
          console.log(`disableIcon: ${this.disableAddButton}`);
          this.$store.dispatch(this.disableIcon, this.id);
          this.$swal({
            title: this.$t('ui.common.disabled'),
            text: `${this.$t('ui.common.disabled')} ${this.typeLabel.toLowerCase()}: ${this.itemLabel}`,
            icon: 'success',
            confirmButtonClass: 'btn btn-success btn-fill',
            buttonsStyling: false
          });
        }
      });
    },
    handleEdit() {
      console.log(`handleEdit id: ${this.id}`);
      console.log(`handleEdit detailIcon: ${this.editIcon}`);
      console.log(`handleEdit 1: ${this.localePath({name:"dashboard-states"})}`);
      console.log(`handleEdit 2: ${this.localePath({name:this.editIcon, params: {id: this.id}})}`);
      // this.$router.push(this.localePath({name:"dashboard-states"}));
      // this.$router.push(this.localePath({name:this.detailIcon}));

      this.$router.push(this.localePath({name:this.editIcon, params: {id: this.id}}));
    },
    handleEnable() {
      this.$swal({
        title: `${this.$t('ui.common.enable')} ${this.typeLabel.toLowerCase()}? <br> ${this.itemLabel}`,
        text: this.$t('ui.phrase.gateway_maybe_need_rebooted_after_change'),
        icon: 'question',
        showCancelButton: true,
        confirmButtonClass: 'btn btn-success btn-fill',
        cancelButtonClass: 'btn btn-danger btn-fill',
        confirmButtonText: 'Yes, enable it!',
        buttonsStyling: false
      }).then(result => {
        if (result.value) {
          this.$store.dispatch(this.enableIcon, this.id);
          this.$swal({
            title: this.$t('ui.common.enabled'),
            text: `${this.$t('ui.common.enabled')} ${this.typeLabel.toLowerCase()}: ${this.itemLabel}`,
            icon: 'success',
            confirmButtonClass: 'btn btn-success btn-fill',
            buttonsStyling: false
          });
        }
      });
    },
    handleReload() {
      this.$swal({
        title: this.$t('ui.modal.titles.on_it'),
        text: this.$t('ui.modal.messages.refreshing_data'),
        icon: 'success',
        showConfirmButton: false,
        timer: 1200
      });
      if (this.dashboardFetchData != null) {
        this.dashboardFetchData()
      }
    },
  }
};
</script>

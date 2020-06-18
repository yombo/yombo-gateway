import DashboardRowActions from "@/components/Dashboard/DashboardRowActions";

import { GW_Device } from '@/models/device'
import { GW_Device_Type } from '@/models/device_type'
import { GW_Gateway } from '@/models/gateway'
import { GW_Location } from '@/models/location'

export const dashboardApiCoreMixin = {
  components: {
    DashboardRowActions,
  },
  computed: {
    gateway_id: function() {
      return this.$store.state.nuxtenv.gateway_id;
    },
  },
  methods: {
    getDevice(item_id) {
      let item = GW_Device.query().where('id', item_id).first();
      if (item == null) {
        return new GW_Device().$toJson();
      }
      return item;
    },
    getDeviceType(item_id) {
      let item = GW_Device_Type.query().where('id', item_id).first();
      if (item == null) {
        return new GW_Device_Type().$toJson();
      }
      return item;
    },
    getGateway(item_id) {
      let item = GW_Gateway.query().where('id', item_id).first();
      if (item == null) {
        return new GW_Gateway().$toJson();
      }
      return item;
    },
    getLocation(item_id) {
      let item = GW_Location.query().where('id', item_id).first();
      if (item == null) {
        return new GW_Location().$toJson();
      }
      return item;
    },
  },
  mounted() {
    this.dashboardFetchData(false);
  },
};

import { dashboardApiCoreMixin } from "./dashboardApiCoreMixin.js";
import DashboardDisplayItem from '@/components/Dashboard/DashboardDisplayItem.vue';

export const dashboardApiItemMixin = {
  components: {
    DashboardDisplayItem,
  },
  mixins: [dashboardApiCoreMixin],
  computed: {
    dashboardQueriedData() {
      let result = this.displayItem;
      if (this.dashboardSearchQuery.length > 0) {
        result = this.dashboardSearchedData;
      }
      return result;
    },
  },
  data() {
    return {
      id: this.$route.params.id,
      displayItem: null,
      apiErrors: null,
    };
  },
};

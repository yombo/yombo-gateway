/**
 * Common items meant for the primary display component.
 */

export const commonMixin = {
  head() {
    return {
      title: `${this.metaPageTitle} - ${this.systemInfo.label}`,
    }
  },
  data() {
    return {
      metaPageTitle: 'Yombo'
    }
  },
  computed: {
      systemInfo: function () {
        if ("$store" in this) {
          return this.$store.state.gateway.systeminfo;
        }
        return {};
      },
    },
  methods: {
    str_limit(value, size) {
      if (!value) return '';
      value = value.toString();

      if (value.length <= size) {
        return value;
      }
      return value.substr(0, size) + '...';
    }
  }
};

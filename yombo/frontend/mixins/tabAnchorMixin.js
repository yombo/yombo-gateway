
export const tabAnchorMixin = {
  data () {
    return {
      tabAnchorIndex: 0,
      tabAnchors: ["unknown"]
    }
  },
  methods: {
    // Used by tabs to change the URL anchor
    tabAnchorChange(anchor) {
      this.$router.push({path: `#${anchor}`});
    },
    // Setup the available tabs, should be an array (list of strings).
    tabAnchorSetup(anchors) {
      this.tabAnchors = anchors;
      this.tabAnchorIndex = this.tabAnchors.findIndex(tab => tab === this.$route.hash);
    }
  },
};

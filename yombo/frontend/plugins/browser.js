import extend from '~/util/extend-vue-app'
import moment from "moment";

export default async function ({ app }) {
	extend(app, {
	  data: {
    window: {
      width: 0,
      height: 0
      }
    },
    created() {
      window.addEventListener('resize', this.handleResize)
      this.handleResize();
    },
    destroyed() {
      window.removeEventListener('resize', this.handleResize)
    },
    methods: {
      handleResize() {
        this.window.width = window.innerWidth;
        this.window.height = window.innerHeight;
      },
    },
    watch: {
      '$i18n.locale': function show(newVal) {
        moment.locale(newVal);
      },
    },
	})
}

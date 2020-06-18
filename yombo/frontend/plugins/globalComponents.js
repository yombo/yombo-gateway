import Button from '@/components/Common/Button.vue';
import Card from '@/components/Common/Cards/Card.vue';
import DropDown from '@/components/Common/Dropdown.vue';
import fgInput from '@/components/Common/Inputs/formGroupInput.vue';
import { Input, InputNumber, Tooltip, Popover } from 'element-ui';
import moment from 'moment'
import VueMoment from 'vue-moment'
import VueSweetalert2 from 'vue-sweetalert2';

/**
 * You can register global components here and use them as a plugin in your main Vue instance
 */

const GlobalComponents = {
  install(Vue) {
    Vue.component('drop-down', DropDown);
    Vue.component('card', Card);
    Vue.component('fg-input', fgInput);
    Vue.component('n-button', Button);
    Vue.component(Input.name, Input);
    Vue.component(InputNumber.name, InputNumber);
    Vue.use(Popover);
    Vue.use(Tooltip);
    Vue.use(VueMoment, { moment });
    Vue.use(VueSweetalert2);
    Vue.use(require('vue-cookies'));
  }
};

export default GlobalComponents;

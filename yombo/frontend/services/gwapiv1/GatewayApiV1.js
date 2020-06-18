import { generic_library } from '@/services/gwapiv1/generic_library';

import authkeys from '@/services/gwapiv1/authkeys';
import current_user from '@/services/gwapiv1/current_user';
import debug from '@/services/gwapiv1/debug';
import frontend from '@/services/gwapiv1/frontend';
import system from '@/services/gwapiv1/system';

export default {
    atoms() {
      return generic_library("atoms", ['all', 'fetchOne']);
    },
    authkeys() {
      return authkeys;
    },
    automation_rules() {
      return generic_library("automation_rules", ['all', 'fetchOne']);
    },
    categories() {
      return generic_library("categories", ['all', 'fetchOne']);
    },
    commands() {
      return generic_library("commands");
    },
    configs() {
      return generic_library("configs");
    },
    current_user () {
      return current_user;
    },
    debug() {
      return debug;
    },
    device_commands() {
      return generic_library("device_commands", ['all', 'fetchOne']);
    },
    device_command_inputs() {
      return generic_library("device_command_inputs");
    },
    device_states() {
      return generic_library("device_states", ['all', 'fetchOne']);
    },
    device_types() {
      return generic_library("device_types");
    },
    device_type_commands() {
      return generic_library("device_type_commands");
    },
    devices() {
      let common = generic_library("devices");
      common['sendCommand'] = function(device_id, command_id, args = {}) {
        // Arguments can accept:
        // pin_code - Pin Code to pass to the device for validation
        // delay - Number of seconds (or float) to delay sending the command
        // max_delay - If for some reason the command doesn't fire within at the delay and the system eventually
        //             catches up, don't fire if max_delay has been reached.
        // not_before - Can supply EPOCH time instead of delay if desired.
        // not_after - Can supply EPOCH time instead of max_delay if desired.
        // inputs - Object (python dict) to send to the device command, such as brightness.

        console.log(`sendCommand: ${device_id} - ${command_id}`);
        return window.$nuxt.$gwapiv1axios.post(`lib/devices/${device_id}/command/${command_id}`, args);
      };
      return common;
    },
    discovery() {
      return generic_library("discovery");
    },
    frontend() {
      return frontend;
    },
    gateways() {
      return generic_library("gateways");
    },
    gateway_modules() {
      return generic_library("gateway_modules");
    },
    locations() {
      // console.log(generic_library("locations"));
      return generic_library("locations");
    },
    nodes() {
      return generic_library("nodes");
    },
    roles() {
      return generic_library("roles");
    },
    scenes() {
      return generic_library("scenes");
    },
    states() {
      return generic_library("states");
    },
    system () {
      return system;
    },
    users () {
      return generic_library("users");
    },
    variable_data () {
      return generic_library("variable_data");
    },
    variable_fields () {
      return generic_library("variable_fields");
    },
    variable_groups () {
      return generic_library("variable_groups");
    },
    manual_call () {
      return {
        "get": function(path) {
          return window.$nuxt.$gwapiv1axios.get(path);
        },
        "delete": function(path) {
          return window.$nuxt.$gwapiv1axios.delete(path);
        },
        "patch": function(path, data) {
          return window.$nuxt.$gwapiv1axios.patch(path, data);
        },
        "post": function(path, data) {
          return window.$nuxt.$gwapiv1axios.post(path, data);
        },
        "put": function(path, data) {
          return window.$nuxt.$gwapiv1axios.put(path, data);
        },
      };
    },
}

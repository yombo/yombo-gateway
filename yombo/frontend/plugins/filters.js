/**
 * Various filters used for components.
 */
import Vue from "vue";

/**
 * Converts a null (and hence undefined) value to a blank string.
 */
function hide_null(value) {
  if (variable == null) {
    return ""
  }
  return value
}

/**
 * The value is encrypted, this will return ui.common.encrypted_data"
 */
function mask_encrypted(value) {
  if (typeof value === "string" && value.startsWith("-----BEGIN PGP MESSAGE-----")) {
    return 'ui.common.encrypted_data';
  }
  return value
}

/**
 * Converts a public field to: private, public_pending, public
 */
function publicstr(value) {
  if (value == 0) {
    return "ui.common.private"
  }
  if (value == 1) {
    return "ui.common.public_pending"
  }
  if (value == 2) {
    return "ui.common.public"
  }
  return "ui.common.unknown"
}

/**
 * Converts a status field to disabled, enabled, deleted.
 */
function status(value) {
  if (value == 0) {
    return "ui.common.disabled"
  }
  if (value == 1) {
    return "ui.common.enabled"
  }
  if (value == 2) {
    return "ui.common.deleted"
  }
  return "ui.common.unknown"
}

/**
 * Return true if the input seems positive or false if it seems negative.
 *
 * Positive can true (bool) or works like: yes, open, on, opened, alive, running.
 */
function true_false(value) {
  if (typeof value === "boolean") {
    return value;
  }
  if (typeof value === "string") {
    return ["true", "1", "open", "opened", "on", "running", "alive"].includes(value.toLocaleString());
  }
  if (Number.isInteger(value)) {
    if (value == 1) {
      return true;
    }
  }
  return false
}

/**
 * Like true_false, but returns a string instead of a bool.
 */
function true_false_string(value) {
  return true_false(value).toString();
}

/**
 * Return "yes" if the input seems positive or "no" if it seems negative.
 *
 * Positive can true (bool) or works like: yes, open, on, opened, alive, running.
 */
function yes_no(value) {
  if (true_false(value)) {
    return "yes"
  } else {
    return "no"
  }
}

Vue.filter('hide_null', hide_null);
Vue.filter('mask_encrypted', mask_encrypted);
Vue.filter('public', publicstr);
Vue.filter('status', status);
Vue.filter('true_false', true_false);
Vue.filter('true_false_string', true_false_string);
Vue.filter('yes_no', yes_no);
Vue.prototype.$filters = Vue.options.filters

/**
 * Various filters used for components.
 */
import Vue from "vue";
import moment from 'moment'

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

function lowercase(value) {
  console.log(`lowercase: ${value}`);
  return value.toLowerCase();
}

/**
 * The following functions convert epoch to varioius standard formats.
 *
 * Locale detection changes are watched in: /frontend/plugins/root_items.js
 */

// 1585473840 -> Mar 29, 2020
function epoch_to_date(value, format = "ll") {
  console.log(`epoch_to_date: ${value} = ${format}`);
  return moment.unix(parseInt(value)).format(format);
}

// 1585473840 -> 3/29/2020
function epoch_to_date_terse(value, format = "l") {
  return moment.unix(value).format(format);
}

// 1585473840 -> Mar 29, 2020 2:24:00 AM
function epoch_to_datetime(value, format = "ll LTS") {
  return moment.unix(value).format(format);
}

// 1585473840 -> 3/29/2020 2:24:00 AM
function epoch_to_datetime_terse(value, format = "l LTS") {
  return moment.unix(value).format(format);
}

Vue.filter('lowercase', lowercase);
Vue.filter('epoch_to_date', epoch_to_date);
Vue.filter('epoch_to_date_terse', epoch_to_date_terse);
Vue.filter('epoch_to_datetime', epoch_to_datetime);
Vue.filter('epoch_to_datetime_terse', epoch_to_datetime_terse);
Vue.filter('hide_null', hide_null);
Vue.filter('mask_encrypted', mask_encrypted);
Vue.filter('public', publicstr);
Vue.filter('status', status);
Vue.filter('true_false', true_false);
Vue.filter('true_false_string', true_false_string);
Vue.filter('yes_no', yes_no);
Vue.filter('str_limit', function (value, size) {
  if (!value) return '';
  value = value.toString();

  if (value.length <= size) {
    return value;
  }
  return value.substr(0, size) + '...';
});
Vue.prototype.$filters = Vue.options.filters

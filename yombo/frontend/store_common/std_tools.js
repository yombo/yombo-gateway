import { a_common } from '@/store_common/db_actions'
import { m_common } from '@/store_common/db_mutations'
import { g_common} from '@/store_common/db_getters'

// Various common tools that don't fit anywhere else.

function common_store(settings) {
  settings = validate_settings(settings);
  return {
    state: common_states(settings),
    actions: a_common(settings),
    mutations: m_common,
    getters: g_common,
  }
}

function common_states(settings) {
  return {
    api_source: null,
    last_download_at: null,
    model_name: settings.model_name,
    refresh_timeout: settings.refresh_timeout,
  }
}

function validate_settings(settings) {
  // Standardize the incoming payload with all the options.
  if (settings == null) { // Catch null and undefined
    settings = {}
  }

  if ( settings.api_source === undefined) {  // Turns out, this is a fast way to check.
    settings.api_source = "gw";
  }
  if ( settings.refresh_timeout === undefined) {
    settings.refresh_timeout = 60;
  }
  return settings;
}

export {
  common_store,
  common_states,
  validate_settings,
}

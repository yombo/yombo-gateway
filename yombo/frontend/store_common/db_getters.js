import humanizeDuration from "humanize-duration";

function g_data_age(state) {
  return Date.now() - state.last_download_at;
}

function g_display_source(state, getters, locale) {
  return getters['data_source'];
}

function g_display_age(state, getters, locale) {
  if (state.last_download_at == 0 || state.last_download_at == null  ) {
    return "never";
  }
  if(locale == "es_419") locale = "es";
  else if(locale == "pt_BR") locale = "pt";
  else if(locale == "pt_BR") locale = "pt";
  return humanizeDuration(Date.now() - state.last_download_at,
    { language: locale, round: true, fallbacks: ["en"] });
}

let g_common = {
  data_age: state => () => {
    return g_data_age(state)
  },
  data_source: state => () => {
    return g_data_age(state)
  },
  display_age: (state, getters) => (locale) => {
    return g_display_age(state, getters, locale)
  }
};

export {
  g_data_age,
  g_display_age,
  g_common,
}

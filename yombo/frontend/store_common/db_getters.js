import humanizeDuration from "humanize-duration";

function g_data_age(settings, state) {
  return Date.now() - state.last_download_at;
}

function g_display_age(settings, state, getters, locale) {
  return humanizeDuration(getters['data_age'](), { language: locale, round: true });
}

export {
  g_data_age,
  g_display_age,
}

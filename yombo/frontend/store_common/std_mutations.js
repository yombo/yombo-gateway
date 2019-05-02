// Standard mutations - don't interact with the database.

async function m_set_data(settings, state, payload) {
  state.data = {};
  Object.keys(payload).forEach(key => {
    state.data[payload[key]['attributes']['id']] = payload[key]['attributes']
  });
  state.last_download_at = Number(Date.now());
  window.$nuxt.$bus.$emit('store_' + settings.name + '_updated', state.last_download_at);
}

async function m_update(settings, state, payload) {
  state.data[payload[key]['attributes']['id']] = payload[key]['attributes']
  window.$nuxt.$bus.$emit('store_' + settings.name + '_updated', state.last_download_at);
}

export {
  m_set_data,
  m_update,
}

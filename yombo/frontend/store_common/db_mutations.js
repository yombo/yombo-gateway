async function m_set_data(settings, state, payload) {
  var Model = settings.model;
  Model.deleteAll();
  Object.keys(payload).forEach(key => {
    Model.insert({
      data: payload[key]['attributes'],
    });
  });
  state.last_download_at = Number(Date.now());
  window.$nuxt.$bus.$emit('store_' + Model.entity + '_updated', state.last_download_at);
}

async function m_update(settings, state, payload) {
  var Model = settings.model;
  Model.insert({
    data: payload,
  });
}

export {
  m_set_data,
  m_update,
}

import database from '@/database/index'

async function do_inserts(settings, incoming) {
  if (!(incoming instanceof Array)) {
    incoming = [incoming];
  }
  let Model = null;
  let api_source = settings.api_source;
  let model_name = null;
  let temp_model_name = null;
  let models_updated = {};
  Object.keys(incoming).forEach(key => {
    temp_model_name = `${settings.api_source}_${incoming[key]['type']}`
    if (model_name !== temp_model_name || Model === null) {
      model_name = temp_model_name;
      if (!(model_name in models_updated)) {
        models_updated[model_name] = [];
      }
      Model = database.model(model_name);
      Model.commit((state) => {
        state.api_source = api_source;
      });
    }
    Model.insert({
      data: incoming[key]['attributes'],
    });
    models_updated[model_name].push(incoming[key]['id']);
  });
  return models_updated;
}

async function m_set_data(state, data) {
  let settings = data[0];
  let payload = data[1];

  let models_updated_data = await do_inserts(settings, payload['data']);

  let models_updated_includes = {}
  if(typeof(payload.included) !== "undefined") {
    models_updated_includes = await do_inserts(settings, payload['included']);
  }

  let models_updated = {...models_updated_data, ...models_updated_includes};
  if (Object.keys(models_updated).length >= 0) {
    for (let key in models_updated) {
      let ids = models_updated[key];
      window.$nuxt.$bus.$emit(`store_${key}_updated`, ids);
    }
  }
}

let m_common = {
  SET_DATA(state, payload) { // Clears all previous data and loads it.
    m_set_data(state, payload);
  },
  touch_downloaded(state, payload) {
    let settings = payload[0];
    state.last_download_at = Number(Date.now());
    state.api_source = settings.api_source;
    state.model_name = settings.model_name;
  }
};

export {
  m_set_data,
  m_common
}

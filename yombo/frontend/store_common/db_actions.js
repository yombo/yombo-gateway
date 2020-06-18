import database from '@/database/index'

function get_api_reference(settings) {
  if (settings.api_source === "gw") {
    return window.$nuxt.$gwapiv1[settings.end_point_name]();
  } else if (settings.api_source === "yombo") {
    return window.$nuxt.$yboapiv1[settings.end_point_name]();
  } else {
    return null;
  }
}

function parse_payload_all(payload) {
  let results = {};
  if (typeof payload === 'object' && payload !== null) {
    let query_string = {};
    if (Object.keys(payload).includes("filter")) {
      for (let property in payload["filter"]) {
        query_string[`filter[${property}]`] = payload["filter"][property];
      }
    }
    if (Object.keys(query_string).length > 0) {
      results["query_string"] = "?" + Object.keys(query_string).map(key => key + '=' + query_string[key]).join('&');
    }
  }
  return results;
}

async function a_fetch(settings, commit, dispatch, state, payload) {
  let Model = database.model(`${settings.api_source}_${settings.model_name}`);
  Model.deleteAll();
  const api_reference = get_api_reference(settings);
  await api_reference.all(parse_payload_all(payload))
    .then(function (response) {
      commit('SET_DATA', [settings, response.data]);
      commit('touch_downloaded', [settings, response.data]);
      // this.$bus.$emit(`api.${settings.api_source}.${settings.model_name}.fetch`, 'received');
      return true;
    });
}

async function a_fetchOne(settings, commit, dispatch, state, payload) {
  const api_reference = get_api_reference(settings);
  await api_reference.fetchOne(payload)
    .then(function (response) {
      commit('SET_DATA', [settings, response.data]);
      commit('touch_downloaded', [settings, response.data]);
      // this.$bus.$emit(`api.${settings.api_source}.${settings.model_name}.fetchOne`, payload.id);
      return true;
    });
}

async function a_refresh(settings, commit, dispatch, state, payload) {
  let refresh_timeout = 60;
  if('refresh_timeout' in settings) {
    refresh_timeout = settings.refresh_timeout
  }
  if (state.last_download_at === null || state.last_download_at <= Math.floor(Date.now() - (refresh_timeout*1000))) {
    await a_fetch(settings, commit, dispatch, state, payload)
  }
}

async function a_update(settings, commit, dispatch, state, payload) {
  const api_reference = get_api_reference(settings);
  let id = payload.id;
  delete payload.id;
  await api_reference.patch(id, payload)
    .then(function (response) {
      commit('UPDATE', response.data['data']['attributes']);
      // this.$bus.$emit(`api.${settings.api_source}.${settings.model_name}.update`, id);
      return response.data['data']['attributes']['status']
    });
}

async function a_enable(settings, commit, dispatch, state, payload) {
  const api_reference = get_api_reference(settings);
  await api_reference.patch(payload.id, {status: 1})
    .then(function (response) {
      // console.log("enable results:");
      // console.log(response);
      commit('UPDATE', response.data['data']['attributes']);
      // this.$bus.$emit(`api.${settings.api_source}.${settings.model_name}.update`, payload.id);
      return response.data['data']['attributes']['status']
    });
}

async function a_delete(settings, commit, dispatch, state, payload) {
  const api_reference = get_api_reference(settings);
  await api_reference.delete(payload)
    .then(function (response) {
      // console.log(response);
      // commit('DELETE', response.data['data']['attributes']);
      // this.$bus.$emit(`api.${settings.api_source}.${settings.model_name}.delete`, payload.id);
      return response.data['data']['attributes']
    });
}

async function a_delete_with_status(settings, commit, dispatch, state, payload) {
  const api_reference = get_api_reference(settings);
  await api_reference.patch(payload.id, {status: 0})
    .then(function (response) {
      // console.log("delete status results:");
      // console.log(response);
      commit('UPDATE', response.data['data']['attributes']);
      // this.$bus.$emit(`api.${settings.api_source}.${settings.model_name}.delete`, payload.id);
      // commit('api_source', api_source)
      return response.data['data']['attributes']['status']
    });
}


async function a_disable(settings, commit, dispatch, state, payload) {
  const api_reference = get_api_reference(settings);
  await api_reference.patch(payload.id, {status: 0})
    .then(function (response) {
      // console.log("disable results:");
      // console.log(response);
      commit('UPDATE', response.data['data']['attributes']);
      // this.$bus.$emit(`api.${settings.api_source}.${settings.model_name}.disable`, payload.id);
      return response.data['data']['attributes']['status']
    });
}

function a_common(settings) {
  return {
    async fetch({commit, dispatch, state}, payload) {
      await a_fetch(settings, commit, dispatch, state, payload);
    },
    async fetchOne({commit, dispatch, state}, payload) {
      await a_fetchOne(settings, commit, dispatch, state, payload);
    },
    async refresh({commit, dispatch, state}, payload) {  // Doesn't need api, just calls fetch if needed.
      await a_refresh(settings, commit, dispatch, state, payload);
    },
    async update({commit, dispatch, state}, payload) {
      await a_update(settings, commit, dispatch, state, payload);
    },
    async delete({commit, dispatch, state}, payload) {
      await a_delete(settings, commit, dispatch, state, payload);
    },
    async delete_with_status({commit, dispatch, state}, payload) {
      await a_delete_with_status(settings, commit, dispatch, state, payload);
    },
    async enable({commit, dispatch, state}, payload) {
      await a_enable(settings, commit, dispatch, state, payload);
    },
    async disable({commit, dispatch, state}, payload) {
      await a_disable(settings, commit, dispatch, state, payload);
    },
  }
};

export {
  a_fetch,
  a_fetchOne,
  a_refresh,
  a_update,
  a_enable,
  a_delete,
  a_delete_with_status,
  a_disable,
  a_common,
}

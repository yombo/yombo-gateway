import { g_data_age, g_display_age } from '@/store_common/db_getters'

export const state = () => ({
  data: {},
  last_download_at: 0
});

export const actions = {
  fetch( { commit }) {
    let response;

    try {
      response = window.$nuxt.$gwapiv1.debug().devices()
        .then(response => {
          // console.log(response.data)
          commit('SET_DATA', response.data['data'])
        });
    } catch (ex) {  // Handle error
      console.log("pages/index: has an error");
      console.log(ex);
      return
    }
  },
    refresh( { state, dispatch }) {
    if (state.last_download_at <= Math.floor(Date.now()/1000) - 120 || state.gwLabel == null) {
      dispatch('fetch');
    }
  }
};

export const mutations = {
  SET_DATA (state, data) {
    state.data = [];
    data.forEach(function (item, index) {
      state.data.push(item["attributes"])
    });
    state.last_download_at = Number(Date.now());
  }
};

export const getters = {
  data_age: state => () => {
    return g_data_age(state)
  },
  display_age: (state, getters) => (locale) => {
    return g_display_age(state, getters, locale)
  },
  columns: (state) => () => {
    // console.log(state.data[0])
    // if (typeof(state.data[0]) == "undefined" && state.data.length == 0) { return []}
    var keys = Object.keys(state.data[0]);
    var results = [];
    keys.forEach(function (item, index) {
      results.push({prop: item})
    });
    return results
  }
};

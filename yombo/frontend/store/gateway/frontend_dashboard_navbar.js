export const state = () => ({
  data: {},
  last_download_at: 0
});

export const actions = {
  fetch( { commit }) {
    let response;

    try {
      response = window.$nuxt.$gwapiv1.frontend().navbar_items()
        .then(response => {
          commit('SET_DATA', response.data)
        });
    } catch (ex) {  // Handle error
      console.log(ex);
      return
    }
  },
    // will only refresh if more than 1 hour has elapsed or the token expires within 2 hours.
    refresh( { state, dispatch }) {
    if (state.last_download_at <= Math.floor(Date.now()/1000) - 3600) {
      dispatch('fetch');
    }
  }
};

export const mutations = {
  SET_DATA (state, data) {
    state.data = data;
    state.last_download_at = Math.floor(Date.now() / 1000);
  }
};

// export const getters = {
//   data_age: state => () => {
//     return g_data_age(state)
//   },
//   display_age: (state, getters) => (locale) => {
//     return g_display_age(state, getters, locale)
//   }
// };

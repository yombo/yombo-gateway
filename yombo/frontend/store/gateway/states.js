import { a_fetch, a_refresh, a_fetchOne } from '@/store_common/db_actions'

import { m_set_data, m_update } from '@/store_common/std_mutations'
import { g_data_age, g_display_age } from '@/store_common/db_getters'

export const state = () => ({
  data: {},
  last_download_at: 0
});

function store_settings() {
  return {
    api: window.$nuxt.$gwapiv1.states(),
    api_all: window.$nuxt.$gwapiv1.states().all,
    name: 'states',
  };
}

export const actions = {
  async fetch( { commit, dispatch }) {
    // console.log(window.$nuxt.$gwapiv1.states().all);
    await a_fetch(store_settings(), commit);
  },
  async fetchOne( { commit, dispatch }, payload) {
    await a_fetchOne(store_settings(), commit, payload);
  },
  async refresh({ state, dispatch }) {  // Doesn't need api, just calls fetch if needed.
    await a_refresh(store_settings(), state, dispatch);
  },
};

export const mutations = {
  SET_DATA(state, payload) { // Clears all previous data and loads it.
    m_set_data(store_settings(), state, payload);
  },
  UPDATE(state, payload) { // Clears all previous data and loads it.
    m_update(store_settings(), state, payload);
  },
};

export const getters = {
  data_age: state => () => {
    return g_data_age(state)
  },
  display_age: (state, getters) => (locale) => {
    return g_display_age(state, getters, locale)
  }
};

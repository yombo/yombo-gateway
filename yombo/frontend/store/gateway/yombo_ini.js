import { a_fetch, a_refresh, a_fetchOne } from '@/store_common/db_actions'

import { m_set_data, m_update } from '@/store_common/std_mutations'
import { g_data_age, g_display_age } from '@/store_common/db_getters'

export const state = () => ({
  data: {},
  last_download_at: 0
});

function store_settings() {
  return {
    api: window.$nuxt.$gwapiv1.atoms(),
    api_all: window.$nuxt.$gwapiv1.atoms().all,
    name: 'atoms',
  };
}

export const actions = {
  async fetch( { commit, dispatch }) {
    // console.log(window.$nuxt.$gwapiv1.atoms().all);
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
    return g_data_age(store_settings(), state)
  },
  display_age: (state, getters) => (locale) => {
    return g_display_age(store_settings(), state, getters, locale)
  }
};

import Location from '@/models/location'

import { a_fetch, a_refresh, a_fetchOne, a_update, a_enable, a_delete_with_status,
         a_disable } from '@/store_common/db_actions'

import { m_set_data, m_update } from '@/store_common/db_mutations'
import { g_data_age, g_display_age } from '@/store_common/db_getters'

export const state = () => ({
  last_download_at: 0
});

function store_settings() {
  return {
    api: window.$nuxt.$yboapiv1.locations(),
    api_all: window.$nuxt.$yboapiv1.locations().all,
    name: 'locations',
    model: Location,
    refresh_age: 7200,
  };
}

export const actions = {
  async fetch( { commit, dispatch }) {
    // let feters = a_fetch.bind(this);
    await a_fetch(store_settings(), commit);
  },
  async fetchOne( { commit, dispatch }, payload) {
    await a_fetchOne(store_settings(), commit, payload);
  },
  async refresh({ state, dispatch }) {  // Doesn't need api, just calls fetch if needed.
    await a_refresh(store_settings(), state, dispatch);
  },
  async update({ commit, state, dispatch }, payload) {
    await a_delete_with_status(store_settings(), commit, state, dispatch, payload);
  },
  async delete({ commit, state, dispatch }, payload) {
    await a_update(store_settings(), commit, state, dispatch, payload);
  },
  async enable({ commit, state, dispatch }, payload) {
    await a_enable(store_settings(), commit, state, dispatch, payload);
  },
  async disable({ commit, state, dispatch }, payload) {
    await a_disable(store_settings(), commit, state, dispatch, payload);
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

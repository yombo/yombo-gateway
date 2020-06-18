import { common_store } from '@/store_common/std_tools'

let settings = {
  api_source: 'gw',
  end_point_name: 'states',
  model_name: 'states',
  refresh_timeout: 300,
};

let store = common_store(settings);
export const state = () => store.state;
export const actions = store.actions;
export const mutations = store.mutations;
export const getters = store.getters;

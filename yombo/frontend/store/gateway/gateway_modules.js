import { common_store } from '@/store_common/std_tools'

let settings = {
  api_source: 'gw',
  end_point_name: 'gateway_modules',
  model_name: 'gateway_modules',
  refresh_timeout: 60,
};

let store = common_store(settings);
export const state = () => store.state;
export const actions = store.actions;
export const mutations = store.mutations;
export const getters = store.getters;

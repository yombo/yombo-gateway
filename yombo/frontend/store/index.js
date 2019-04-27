import VuexORM from '@vuex-orm/core'
import database from '@/database'

export const plugins = [
  VuexORM.install(database)
]

export const state = () => ({
  counter: 0
});

export const mutations = {
  increment (state) {
    state.counter++
  }
};

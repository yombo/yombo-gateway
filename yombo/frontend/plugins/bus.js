// From: https://github.com/nuxt/nuxt.js/issues/1139
import Vue from 'vue';

export default (ctx, inject) => {
  const bus = new Vue;
  inject('bus', bus);
};
//
// export default function ( {app, store} ){
//   console.log("adding busss....")
//   app.$bus = new Vue
//   if (store)
//     store.$bus = app.$bus
// }

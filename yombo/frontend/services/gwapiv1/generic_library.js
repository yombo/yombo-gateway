function get_payload_item(payload, item, default_value = "") {
  let results = default_value;
  if (typeof payload === 'object' || payload !== null) {
    if (Object.keys(payload).includes(item)) {
      results = payload[item];
    }
  }
  return results;
}

function generic_library(path, requested = ['all', 'fetchOne', 'delete', 'patch']) {
  let available = {
    "all": function(payload) {
      let query_string = get_payload_item(payload, "query_string");
      return window.$nuxt.$gwapiv1axios.get(`lib/${path}${query_string}`);
    },
    "fetchOne": function(id) {
      return window.$nuxt.$gwapiv1axios.get(`lib/${path}/${id}`);
    },
    "delete": function(id) {
      // console.log("generic_library - delete");
      return window.$nuxt.$gwapiv1axios.delete(`lib/${path}/${id}`);
    },
    "patch": function(id, data) {
      // console.log("generic_library - patch");
      return window.$nuxt.$gwapiv1axios.patch(`lib/${path}/${id}`, data);
    },
  };

  let results = {};
  for (var index = 0; index < requested.length; index++) {
    results[requested[index]] = available[requested[index]];
  }
  return results;
};

export {
  generic_library,
}


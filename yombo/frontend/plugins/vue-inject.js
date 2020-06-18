import Vue from 'vue';

Vue.prototype.$handleApiErrorResponse = function(error, apiErrors = null) {
  if (apiErrors == null) {
    apiErrors = []
  }
  if (error.code === "ECONNABORTED") {
    return apiErrors.concat([
      {
          "detail": "Connection timed out",
          "status": 503,
          "title": "Service Unavailable",
          "code": "service-unavailable-503"
      }
    ]);
  } else if (error.message === "Network Error") {
    return apiErrors.concat([
      {
          "detail": "Network error",
          "status": 503,
          "title": "Service Unavailable",
          "code": "service-unavailable-503"
      }
    ]);
  } else {
    return apiErrors.concat(error.response.data.errors);
  }
};

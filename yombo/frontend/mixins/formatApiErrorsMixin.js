
export const formatApiErrorsMixin = {
  methods: {
    formatApiErrors(error) {
      let apiErrors = null;
      // console.log("handleApiErrorResponse");
      // console.log(error);
      if (error.code === "ECONNABORTED") {
        apiErrors = [
          {
              "detail": "Connection timed out",
              "status": 503,
              "title": "Service Unavailable",
              "code": "service-unavailable-503"
          }
        ];
      } else if (error.message === "Network Error") {
        apiErrors = [
          {
              "detail": "Network error",
              "status": 503,
              "title": "Service Unavailable",
              "code": "service-unavailable-503"
          }
        ];
      } else {
        console.log(`handle api errpr: ${error}`);
        apiErrors = error.response.data.errors;
      }
      return apiErrors;
    },
    displayApiError(apiError) {
      this.$swal({
        title: `${apiError.title}`,
        text: `${apiError.detail}`,
        icon: 'error',
        confirmButtonClass: 'btn btn-success btn-fill',
        buttonsStyling: false
      });
    }
  },
};

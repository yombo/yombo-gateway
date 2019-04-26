import axios from 'axios'

export default() => {
  let protocol = ('https:' == document.location.protocol ? 'https://' : 'http://');

  let locationPart = ('local' == window.$nuxt.$gwenv.client_location ? 'internal_' : 'external_');
  let portPart = ('https:' == document.location.protocol ? 'http_secure_port' : 'http_port');

  let portName = locationPart + portPart;
  let uriBase =  protocol + document.location.hostname + ":" + window.$nuxt.$gwenv[portName];

  return axios.create({
      baseURL: uriBase + '/api/v1/',
      withCredentials: true,
      headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json'
      }
  })
}


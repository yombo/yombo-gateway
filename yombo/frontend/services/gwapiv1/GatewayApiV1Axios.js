import axios from 'axios';

function GetGWV1Client (env) {
  let protocol = ('https:' == document.location.protocol ? 'https://' : 'http://');
  let locationPart = ('local' == env.client_location ? 'internal_' : 'external_');
  let portPart = ('https:' == document.location.protocol ? 'http_secure_port' : 'http_port');
  let portName = locationPart + portPart;
  let uriBase =  protocol + document.location.hostname + ":" + env[portName];
  return axios.create({
      baseURL: uriBase + '/api/v1/',
      withCredentials: true,
      headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json'
      },
      timeout: 15000,
  })
}

export {GetGWV1Client}

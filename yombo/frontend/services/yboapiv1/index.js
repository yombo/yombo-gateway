import axios from 'axios'

export default() => {
  console.log("creating yomo api axios client");
  // console.log(window.$nuxt.$store.state.gateway.access_token)
    return axios.create({
        baseURL: `https://api.yombo.net/api/v1/`,
        // withCredentials: true,
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': 'user_api_token ' + window.$nuxt.$store.state.gateway.access_token.access_token,
        }
    })
}


import axios from 'axios';

function GetYomboV1Client (access_token) {
    return axios.create({
        baseURL: `https://api.yombo.net/api/v1/`,
        // withCredentials: true,
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': 'user_api_token ' + access_token,
        }
    })
}

export {GetYomboV1Client}

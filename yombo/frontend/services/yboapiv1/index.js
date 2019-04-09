import axios from 'axios'

export default() => {
    return axios.create({
        baseURL: `https://mydev.yombo.net/api/v1/`,
        withCredentials: true,
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    })
}


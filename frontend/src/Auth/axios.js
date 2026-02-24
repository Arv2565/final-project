import axios from 'axios';
import { getCookie } from "../utils.js";
import { jwtDecode } from "jwt-decode";

const baseURL = 'http://localhost:8000/api/';
export const axiosJWT = axios.create({ baseURL })

axiosJWT.interceptors.request.use(async (config) => {
    const date = new Date();
    const token = getCookie('auth'); // Fetches the auth cookie

    if (!token) return config; // If no token, proceed with the request as-is

    const decodedToken = jwtDecode(token); // Decode the token to extract its expiration time
    if (decodedToken.exp * 1000 < date.getTime()) {
        await refresh(); // If token is expired, refresh it
    }

    config.headers.authorization = `Bearer ${getCookie('auth')}`; // Add the valid token to the request headers
    return config;
}, err => Promise.reject(err));

async function refresh() {
    const token = getCookie('ref')
    const data = { token }
    await axios.post(baseURL + "auth/refresh", data)
        .then(res => {
            document.cookie = `auth=${res.data.accessToken}; path=/; secure; samesite=strict`;
            document.cookie = `ref=${res.data.refreshToken}; path=/; secure; samesite=strict`;
        })
        .catch(err => {
            console.log(err)
            document.cookie = `auth=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT`;
            document.cookie = `ref=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT`;
            // Redirect to login if refresh fails
            window.location.href = '/';
        })
}

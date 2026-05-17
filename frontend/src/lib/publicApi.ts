import axios from 'axios'

// No request/response interceptors — safe to use on public pages (login, signup, invite)
// where a 401 should surface as an error, not trigger a redirect to /login.
const publicApi = axios.create({
  baseURL: `${process.env.NEXT_PUBLIC_API_URL}/api/v1`,
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
})

export default publicApi

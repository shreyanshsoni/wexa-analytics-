import axios, { AxiosError } from "axios";
import { useAuthStore } from "@/store/authStore";

const BASE = `${process.env.NEXT_PUBLIC_API_URL}/api/v1`;

const api = axios.create({
  baseURL: BASE,
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
});

// Attach access token on every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Single in-flight refresh promise — prevents concurrent 401s from each triggering
// their own refresh, which would rotate the cookie multiple times and leave all but
// the first with a revoked token, causing an immediate logout.
let refreshing: Promise<string> | null = null;

// On 401: silently refresh the access token using the HTTP-only cookie, then retry once.
// If refresh also fails (cookie expired/revoked), redirect to login.
api.interceptors.response.use(
  (res) => res,
  async (error: AxiosError) => {
    const original = error.config as typeof error.config & { _retry?: boolean };

    if (error.response?.status === 401 && !original?._retry) {
      original._retry = true;

      if (!refreshing) {
        refreshing = axios
          .post(`${BASE}/auth/refresh`, {}, { withCredentials: true })
          .then(({ data }) => {
            const newToken: string = data.data.access_token;
            localStorage.setItem("access_token", newToken);
            return newToken;
          })
          .catch((err) => {
            useAuthStore.getState().clearAuth();
            window.location.href = "/login";
            throw err;
          })
          .finally(() => {
            refreshing = null;
          });
      }

      try {
        const newToken = await refreshing;
        if (original.headers) {
          original.headers.Authorization = `Bearer ${newToken}`;
        }
        return api(original);
      } catch {
        return Promise.reject(error);
      }
    }

    return Promise.reject(error);
  },
);

export default api;

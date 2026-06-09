import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const apiClient = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
})

apiClient.interceptors.request.use((config) => {
  const stored = localStorage.getItem('agrow_auth')
  if (stored) {
    try {
      const { state } = JSON.parse(stored)
      if (state?.token) config.headers.Authorization = `Bearer ${state.token}`
    } catch (_) {}
  }
  return config
})

apiClient.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      // Only redirect to login if it's not the login/register endpoint itself
      const url = err.config?.url || ''
      if (!url.includes('/auth/login') && !url.includes('/auth/register')) {
        localStorage.removeItem('agrow_auth')
        window.location.href = '/login'
      }
    }
    return Promise.reject(err)
  }
)

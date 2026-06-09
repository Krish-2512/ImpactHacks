import { apiClient } from './client'

export const register = (data) => apiClient.post('/auth/register', data).then(r => r.data)
export const login    = (data) => apiClient.post('/auth/login', data).then(r => r.data)
export const getMe    = ()     => apiClient.get('/auth/me').then(r => r.data)
export const updateMe = (data) => apiClient.put('/auth/me', data).then(r => r.data)

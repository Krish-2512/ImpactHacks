import { apiClient } from './client'

export const getNotifications   = ()   => apiClient.get('/notifications/').then(r => r.data)
export const markRead           = (id) => apiClient.put(`/notifications/${id}/read`).then(r => r.data)
export const deleteNotification = (id) => apiClient.delete(`/notifications/${id}`).then(r => r.data)

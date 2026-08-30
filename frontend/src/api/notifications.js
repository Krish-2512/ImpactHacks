import { apiClient } from './client'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const getNotifications   = (unreadOnly = false) =>
  apiClient.get('/notifications/', { params: { unread_only: unreadOnly } }).then(r => r.data)

export const getUnreadCount     = () => apiClient.get('/notifications/count').then(r => r.data)
export const markRead           = (id) => apiClient.put(`/notifications/${id}/read`).then(r => r.data)
export const markAllRead        = () => apiClient.put('/notifications/read-all').then(r => r.data)
export const deleteNotification = (id) => apiClient.delete(`/notifications/${id}`).then(r => r.data)
export const deleteAllRead      = () => apiClient.delete('/notifications/read').then(r => r.data)

export function connectNotificationWS(onMessage) {
  const stored = localStorage.getItem('agrow_auth')
  let token = ''
  try { token = JSON.parse(stored)?.state?.token || '' } catch (_) {}
  if (!token) return () => {}

  const ws = new WebSocket(`${API_URL.replace('http', 'ws')}/notifications/ws?token=${token}`)
  ws.onmessage = (e) => {
    try { onMessage(JSON.parse(e.data)) } catch (_) {}
  }
  return () => ws.close()
}

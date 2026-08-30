import { apiClient } from './client'

export const detectDisease = (file) => {
  const form = new FormData()
  form.append('image', file)
  // Do NOT set Content-Type manually — browser must set it with the multipart boundary
  return apiClient.post('/disease/detect', form, {
    headers: { 'Content-Type': undefined },
  }).then(r => r.data)
}

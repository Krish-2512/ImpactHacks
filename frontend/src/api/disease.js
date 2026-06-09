import { apiClient } from './client'

export const detectDisease = (file) => {
  const form = new FormData()
  form.append('image', file)
  return apiClient.post('/disease/detect', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data)
}

import { apiClient } from './client'

export const queryCropAdvisory = (query, crop = null) =>
  apiClient.post('/rag/query', { query, crop }).then(r => r.data)

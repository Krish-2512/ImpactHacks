import { apiClient } from './client'

export const recommendCrop   = (body)  => apiClient.post('/ml/recommend-crop', body).then(r => r.data)
export const getIrrigation   = (body)  => apiClient.post('/ml/irrigation', body).then(r => r.data)
export const getPriceAnomaly = ()      => apiClient.get('/ml/price-anomaly').then(r => r.data)
export const getModelInfo    = ()      => apiClient.get('/ml/model-info').then(r => r.data)

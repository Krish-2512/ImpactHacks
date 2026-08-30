import { apiClient } from './client'

export const getWeather        = () => apiClient.get('/predict/weather').then(r => r.data)
export const getCropPrices     = () => apiClient.get('/predict/prices').then(r => r.data)
export const getPriceForecast  = (days = 10) => apiClient.get(`/predict/prices/forecast?days=${days}`).then(r => r.data)

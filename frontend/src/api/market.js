import { apiClient } from './client'

export const getProducts      = ()           => apiClient.get('/market/products').then(r => r.data)
export const getFarmers       = ()           => apiClient.get('/market/farmers').then(r => r.data)
export const getFarmerProducts= (id)         => apiClient.get(`/market/farmer/${id}/products`).then(r => r.data)
export const createProduct    = (data)       => apiClient.post('/market/products', data).then(r => r.data)
export const updateProduct    = (id, data)   => apiClient.put(`/market/products/${id}`, data).then(r => r.data)
export const deleteProduct    = (id)         => apiClient.delete(`/market/products/${id}`).then(r => r.data)
export const purchaseProduct  = (id, qty)    => apiClient.post(`/market/products/${id}/purchase`, { quantity: qty }).then(r => r.data)
export const getTransactions  = ()           => apiClient.get('/market/transactions').then(r => r.data)

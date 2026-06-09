import { apiClient } from './client'

export const runAgentCycle  = ()       => apiClient.post('/agents/run-cycle').then(r => r.data)
export const getLatestReport = ()      => apiClient.get('/agents/latest-report').then(r => r.data)
export const getCycleStatus  = (id)    => apiClient.get(`/agents/status/${id}`).then(r => r.data)
export const getCycleHistory = ()      => apiClient.get('/agents/history').then(r => r.data)

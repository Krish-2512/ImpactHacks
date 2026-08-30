import { apiClient } from './client'

export const getFarmHealth    = ()           => apiClient.get('/intelligence/farm-health').then(r => r.data)
export const getRiskScore     = ()           => apiClient.get('/intelligence/risk-score').then(r => r.data)
export const getCropCalendar  = (payload)    => apiClient.post('/intelligence/crop-calendar', payload).then(r => r.data)
export const getDecisionImpact = (payload)  => apiClient.post('/intelligence/decision-impact', payload).then(r => r.data)

// Observability
export const getTrace         = (cycleId)   => apiClient.get(`/observability/traces/${cycleId}`).then(r => r.data)
export const listTraces       = (params)    => apiClient.get('/observability/traces', { params }).then(r => r.data)
export const getObsStats      = (days = 30) => apiClient.get('/observability/stats', { params: { days } }).then(r => r.data)

// Evaluation
export const runEvaluation    = (cycleId)   => apiClient.post(`/evaluation/run/${cycleId}`).then(r => r.data)
export const getEvalResult    = (cycleId)   => apiClient.get(`/evaluation/results/${cycleId}`).then(r => r.data)
export const getEvalDashboard = (days = 30) => apiClient.get('/evaluation/dashboard', { params: { days } }).then(r => r.data)

import { apiClient } from './client'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const runAgentCycle   = (imageBase64 = null) =>
  apiClient.post('/agents/run-cycle', imageBase64 ? { image_base64: imageBase64 } : {}).then(r => r.data)
export const getLatestReport = ()    => apiClient.get('/agents/latest-report').then(r => r.data)
export const getCycleStatus  = (id)  => apiClient.get(`/agents/status/${id}`).then(r => r.data)
export const getCycleHistory = ()    => apiClient.get('/agents/history').then(r => r.data)
export const getMemory       = ()    => apiClient.get('/agents/memory').then(r => r.data)

/**
 * Stream SSE events from a cycle.
 * Returns a cancel function. onEvent is called for each event dict.
 * onDone is called when pipeline finishes or connection drops.
 */
export function streamCycle(cycleId, onEvent, onDone) {
  const stored = localStorage.getItem('agrow_auth')
  let token = ''
  try { token = JSON.parse(stored)?.state?.token || '' } catch (_) {}

  const controller = new AbortController()

  fetch(`${API_URL}/agents/stream/${cycleId}`, {
    headers: { Authorization: `Bearer ${token}` },
    signal: controller.signal,
  }).then(async (res) => {
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) { onDone?.(); break }
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop()
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const event = JSON.parse(line.slice(6))
            onEvent(event)
            if (event.event === 'done') { onDone?.(); return }
          } catch (_) {}
        }
      }
    }
  }).catch(() => onDone?.())

  return () => controller.abort()
}

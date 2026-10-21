import { request } from './client.js'

export function analyzeHygiene(formData, options) {
  return request('/api/hygiene/analyze', {
    method: 'POST',
    body: formData,
    timeout: 180_000,
    ...options,
  })
}

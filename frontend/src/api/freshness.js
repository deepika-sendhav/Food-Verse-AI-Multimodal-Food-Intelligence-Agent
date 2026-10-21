import { request } from './client.js'

export function analyzeFreshness(formData, options) {
  return request('/api/freshness/analyze', {
    method: 'POST',
    body: formData,
    ...options,
  })
}

export function extractFreshnessFeatures(formData, options) {
  return request('/api/freshness/features', {
    method: 'POST',
    body: formData,
    ...options,
  })
}

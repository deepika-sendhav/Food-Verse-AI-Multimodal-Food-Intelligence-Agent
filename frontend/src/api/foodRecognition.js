import { request } from './client.js'

export function analyzeFood(formData, options) {
  return request('/api/food-recognition/analyze', {
    method: 'POST',
    body: formData,
    ...options,
  })
}

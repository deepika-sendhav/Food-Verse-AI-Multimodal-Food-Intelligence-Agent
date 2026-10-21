import { request } from './client.js'

export function generateMealPlan(data, options) {
  return request('/api/meal-plan/generate', {
    method: 'POST',
    body: data,
    ...options,
  })
}

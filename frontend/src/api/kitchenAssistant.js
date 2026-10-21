import { request } from './client.js'

export function generateRecipe(formData, options) {
  return request('/api/kitchen/generate-recipe', {
    method: 'POST',
    body: formData,
    ...options,
  })
}

import { request } from './client.js'

export function getApiHealth() {
  return request('/api/health')
}

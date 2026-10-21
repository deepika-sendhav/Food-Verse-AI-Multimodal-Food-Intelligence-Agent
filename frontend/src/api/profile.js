import { request } from './client.js'

export function getProfileOptions(options) {
  return request('/api/profile/options', options)
}

export function validateProfile(data) {
  return request('/api/profile/validate', { method: 'POST', body: data })
}

export function createProfile(data, options) {
  return request('/api/profile', { method: 'POST', body: data, ...options })
}

export function updateProfile(profileId, data, options) {
  return request(`/api/profile/${encodeURIComponent(profileId)}`, {
    method: 'PUT',
    body: data,
    ...options,
  })
}

export function getProfile(profileId, options) {
  return request(`/api/profile/${encodeURIComponent(profileId)}`, options)
}

export function deleteProfile(profileId, options) {
  return request(`/api/profile/${encodeURIComponent(profileId)}`, {
    method: 'DELETE',
    ...options,
  })
}

import { afterEach, describe, expect, it, vi } from 'vitest'
import { normalizeError, request } from '../api/client.js'

afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

function response(status, body = {}, headers = {}) {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: new Headers(headers),
    json: async () => body,
  }
}

describe('API error normalization', () => {
  it.each([
    [413, {}, 'File too large'],
    [415, {}, 'Unsupported file type'],
    [404, { detail: 'Profile not found.' }, 'Profile not found.'],
    [
      422,
      { detail: [{ loc: ['body', 'file'], msg: 'Field required' }] },
      'file: Field required',
    ],
    [
      422,
      { detail: [{ field: 'age_years', message: 'Out of range' }] },
      'age_years: Out of range',
    ],
    [502, {}, 'The AI returned an unusable answer, please retry'],
    [503, {}, 'Service unavailable or not configured'],
    [504, {}, 'The request timed out'],
  ])('maps status %s', (status, body, message) => {
    expect(normalizeError(null, status, body).message).toBe(message)
  })

  it('reads Retry-After for rate limit responses', () => {
    const error = normalizeError(
      null,
      429,
      { detail: 'Slow down' },
      new Headers({ 'Retry-After': '12' }),
    )
    expect(error.message).toBe('Slow down')
    expect(error.retryAfter).toBe(12)
  })

  it('accepts Retry-After as an HTTP date', () => {
    const retryAt = new Date(Date.now() + 5000).toUTCString()
    const error = normalizeError(
      null,
      429,
      {},
      new Headers({ 'Retry-After': retryAt }),
    )
    expect(error.retryAfter).toBeGreaterThanOrEqual(0)
    expect(error.retryAfter).toBeLessThanOrEqual(5)
  })

  it('maps network failures to the backend connection message', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockRejectedValue(new TypeError('Failed to fetch')),
    )
    await expect(request('/api/test')).rejects.toMatchObject({
      message: 'Cannot reach the backend. Is it running?',
    })
  })

  it('maps plain text error detail', () => {
    expect(
      normalizeError(null, 400, { detail: 'Check your input' }).message,
    ).toBe('Check your input')
  })
})

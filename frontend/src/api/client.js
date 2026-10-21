const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(
  /\/$/,
  '',
)

export class ApiError extends Error {
  constructor(
    message,
    { status = 0, retryAfter = null, fieldErrors = [] } = {},
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.retryAfter = retryAfter
    this.fieldErrors = fieldErrors
  }
}

function detailMessage(body) {
  const detail = body?.detail
  if (typeof detail === 'string') return detail
  if (!Array.isArray(detail)) return ''
  return detail
    .map((item) => {
      const field =
        item.field ??
        (Array.isArray(item.loc) ? item.loc.slice(1).join('.') : '')
      const message = item.message ?? item.msg ?? ''
      return [field, message].filter(Boolean).join(': ')
    })
    .filter(Boolean)
    .join(' · ')
}

export function normalizeError(error, status, body, headers) {
  if (error instanceof ApiError) return error
  if (status === 0 || error instanceof TypeError) {
    return new ApiError('Cannot reach the backend. Is it running?')
  }
  const mapped = {
    400: detailMessage(body) || 'Please check the information and try again.',
    404: detailMessage(body) || 'The requested item could not be found.',
    413: 'File too large',
    415: 'Unsupported file type',
    422: detailMessage(body) || 'Some information needs your attention.',
    429:
      detailMessage(body) ||
      'Too many requests. Please wait before trying again.',
    502: 'The AI returned an unusable answer, please retry',
    503: 'Service unavailable or not configured',
    504: 'The request timed out',
  }
  const message =
    mapped[status] ||
    detailMessage(body) ||
    'Something went wrong. Please try again.'
  const retryValue = headers?.get?.('Retry-After')
  const retrySeconds = retryValue ? Number.parseInt(retryValue, 10) : Number.NaN
  const retryAfter =
    status !== 429 || !retryValue
      ? null
      : Number.isFinite(retrySeconds)
        ? Math.max(0, retrySeconds)
        : Math.max(0, Math.ceil((Date.parse(retryValue) - Date.now()) / 1000))
  const detail = body?.detail
  return new ApiError(message, {
    status,
    retryAfter,
    fieldErrors: Array.isArray(detail) ? detail : [],
  })
}

export async function request(
  path,
  { method = 'GET', body, timeout = 30_000, headers = {}, signal } = {},
) {
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), timeout)
  const abortFromCaller = () => controller.abort()
  if (signal?.aborted) controller.abort()
  signal?.addEventListener('abort', abortFromCaller, { once: true })
  const requestHeaders = { ...headers }
  if (body !== undefined && !(body instanceof FormData))
    requestHeaders['Content-Type'] = 'application/json'
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers: requestHeaders,
      body:
        body === undefined
          ? undefined
          : body instanceof FormData
            ? body
            : JSON.stringify(body),
      signal: controller.signal,
    })
    if (!response.ok) {
      let responseBody = {}
      try {
        responseBody = await response.json()
      } catch {
        responseBody = {}
      }
      throw normalizeError(
        null,
        response.status,
        responseBody,
        response.headers,
      )
    }
    if (response.status === 204) return null
    return response.json()
  } catch (error) {
    if (error instanceof ApiError) throw error
    if (signal?.aborted) {
      const cancelled = new ApiError('Request cancelled')
      cancelled.cancelled = true
      throw cancelled
    }
    if (error?.name === 'AbortError')
      throw new ApiError('The request timed out', { status: 504 })
    throw normalizeError(error, 0)
  } finally {
    window.clearTimeout(timer)
    signal?.removeEventListener('abort', abortFromCaller)
  }
}

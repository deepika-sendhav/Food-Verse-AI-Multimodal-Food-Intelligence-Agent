export function formatLabel(value = '') {
  return value
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

export function splitList(value) {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}

export function displayValue(value, suffix = '') {
  return value === null || value === undefined
    ? 'Not available'
    : `${value}${suffix}`
}

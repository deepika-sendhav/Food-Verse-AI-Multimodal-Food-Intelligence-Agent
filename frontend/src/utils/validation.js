export const IMAGE_LIMIT_BYTES = 10 * 1024 * 1024
export const VIDEO_LIMIT_BYTES = 50 * 1024 * 1024
export const IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp']
export const VIDEO_TYPES = [
  'video/mp4',
  'video/quicktime',
  'video/x-msvideo',
  'video/webm',
]

export function validateUpload(file, { video = false } = {}) {
  if (!file) return 'Choose a file to continue.'
  if (file.size === 0) return 'This file is empty. Choose another file.'
  const acceptedTypes = video ? [...IMAGE_TYPES, ...VIDEO_TYPES] : IMAGE_TYPES
  if (!acceptedTypes.includes(file.type))
    return video
      ? 'Choose a JPG, PNG, WEBP, MP4, MOV, AVI or WEBM file.'
      : 'Choose a JPG, PNG or WEBP image.'
  const extension = file.name.split('.').pop()?.toLowerCase()
  const extensionsByType = {
    'image/jpeg': ['jpg', 'jpeg'],
    'image/png': ['png'],
    'image/webp': ['webp'],
    'video/mp4': ['mp4'],
    'video/quicktime': ['mov'],
    'video/x-msvideo': ['avi'],
    'video/webm': ['webm'],
  }
  if (!extensionsByType[file.type]?.includes(extension))
    return 'File extension does not match its selected type.'
  const limit =
    video && VIDEO_TYPES.includes(file.type)
      ? VIDEO_LIMIT_BYTES
      : IMAGE_LIMIT_BYTES
  if (file.size > limit)
    return `File too large. The limit is ${video && limit === VIDEO_LIMIT_BYTES ? '50 MB' : '10 MB'}.`
  return ''
}

export function numberInRange(value, minimum, maximum) {
  const parsed = Number(value)
  return Number.isFinite(parsed) && parsed >= minimum && parsed <= maximum
}

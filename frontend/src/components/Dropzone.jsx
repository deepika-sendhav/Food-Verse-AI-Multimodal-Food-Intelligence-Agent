import { ImagePlus, Upload } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

export default function Dropzone({
  file,
  onFile,
  accept = 'image/jpeg,image/png,image/webp',
  label = 'Choose an image',
}) {
  const inputRef = useRef(null)
  const [dragging, setDragging] = useState(false)
  const [previewUrl, setPreviewUrl] = useState('')
  useEffect(() => {
    if (
      !file ||
      (!file.type.startsWith('image/') && !file.type.startsWith('video/'))
    ) {
      setPreviewUrl('')
      return undefined
    }
    const url = URL.createObjectURL(file)
    setPreviewUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [file])
  const choose = (selected) => {
    const next = selected?.[0]
    if (next) onFile(next)
    if (inputRef.current) inputRef.current.value = ''
  }
  return (
    <div
      className={`dropzone ${dragging ? 'dropzone--dragging' : ''}`}
      onDragOver={(event) => {
        event.preventDefault()
        setDragging(true)
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(event) => {
        event.preventDefault()
        setDragging(false)
        choose(event.dataTransfer.files)
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        onChange={(event) => choose(event.target.files)}
        aria-label={label}
      />
      {previewUrl && file.type.startsWith('video/') ? (
        <video
          className="dropzone__preview"
          src={previewUrl}
          aria-label={`Local preview of ${file.name}`}
          controls
          muted
        />
      ) : previewUrl ? (
        <img
          className="dropzone__preview"
          src={previewUrl}
          alt={`Preview of ${file.name}`}
        />
      ) : (
        <ImagePlus size={30} aria-hidden="true" />
      )}
      <strong>{file?.name || 'Drop a file here'}</strong>
      <span>{file ? 'Select another file' : 'or browse from your device'}</span>
      <button
        type="button"
        className="button button--quiet"
        onClick={() => inputRef.current?.click()}
      >
        <Upload size={16} /> {label}
      </button>
    </div>
  )
}

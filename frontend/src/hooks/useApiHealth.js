import { useEffect, useState } from 'react'
import { getApiHealth } from '../api/health.js'

export default function useApiHealth() {
  const [health, setHealth] = useState({ status: 'checking', demo: false })
  useEffect(() => {
    let active = true
    let timer
    let controller
    const check = async () => {
      controller = new AbortController()
      try {
        const result = await getApiHealth({ signal: controller.signal })
        if (active) setHealth({ status: 'online', demo: result.demo === true })
      } catch {
        if (active) setHealth({ status: 'offline', demo: false })
      } finally {
        if (active) timer = window.setTimeout(check, 30_000)
      }
    }
    check()
    return () => {
      active = false
      window.clearTimeout(timer)
      controller?.abort()
    }
  }, [])
  return health
}

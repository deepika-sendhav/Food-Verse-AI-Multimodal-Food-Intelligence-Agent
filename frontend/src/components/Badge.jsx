import { formatLabel } from '../utils/format.js'

export default function Badge({ children, tone = 'neutral' }) {
  return (
    <span className={`badge badge--${tone}`}>
      {typeof children === 'string' ? formatLabel(children) : children}
    </span>
  )
}

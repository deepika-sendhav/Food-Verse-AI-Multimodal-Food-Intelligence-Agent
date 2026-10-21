import { Sparkles } from 'lucide-react'

export default function EmptyState({
  title = 'Ready when you are',
  children = 'Add an input and run an analysis to see your results here.',
}) {
  return (
    <div className="empty-state">
      <Sparkles size={25} aria-hidden="true" />
      <h3>{title}</h3>
      <p>{children}</p>
    </div>
  )
}

export default function Skeleton({ lines = 3 }) {
  return (
    <div className="skeleton" aria-label="Loading" role="status">
      {Array.from({ length: lines }, (_, index) => (
        <span key={index} />
      ))}
    </div>
  )
}

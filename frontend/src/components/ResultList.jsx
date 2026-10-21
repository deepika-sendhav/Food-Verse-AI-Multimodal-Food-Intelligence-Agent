export default function ResultList({ title, items = [] }) {
  if (!items?.length) return null
  return (
    <section className="result-list">
      <h3>{title}</h3>
      <ul>
        {items.map((item, index) => (
          <li key={`${item}-${index}`}>{item}</li>
        ))}
      </ul>
    </section>
  )
}

export default function Card({ children, className = '', ...props }) {
  return (
    <section className={`card ${className}`} {...props}>
      {children}
    </section>
  )
}

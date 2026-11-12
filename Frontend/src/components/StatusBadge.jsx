export function StatusBadge({ status }) {
  const label = status || 'Connecting'
  return <span className={`pill ${label === 'healthy' ? 'ok' : ''}`}>{label}</span>
}

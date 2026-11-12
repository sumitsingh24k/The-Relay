const cards = [
  ['Requests', 'total_requests', false], ['p50 latency', 'p50_ms', true], ['p95 latency', 'p95_ms', true],
  ['TTFT', 'ttft_p50_ms', true], ['Rate limits', 'rate_limit_events', false], ['Retries', 'retry_count', false],
]

export function MetricsCards({ metrics = {} }) {
  return <div className="grid">{cards.map(([label, property, milliseconds]) => {
    const value = metrics[property]
    return <article key={property}><small>{label}</small><strong>{value ?? '—'}{milliseconds && value != null ? ' ms' : ''}</strong></article>
  })}</div>
}

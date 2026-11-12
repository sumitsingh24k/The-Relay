import { MetricsCards } from '../components/MetricsCards'
import { ResultsTable } from '../components/ResultsTable'

export function Dashboard({ documents, health, metrics, page }) {
  if (page === 'Documents') return <ResultsTable documents={documents} />
  if (page === 'Performance') return <section className="empty"><h2>Measured performance</h2>
    <p>{metrics?.note || `${metrics?.sample_count || 0} actual request records`}</p><MetricsCards metrics={metrics?.metrics} /></section>
  return <section className="cards">{health && Object.entries(health).map(([name, value]) => (
    <article key={name}><small>{name.toUpperCase()}</small><h2>{value}</h2></article>
  ))}</section>
}

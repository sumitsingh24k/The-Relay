export function ResultsTable({ documents }) {
  if (!documents.length) return <p>No verified documents were returned by the backend.</p>
  return <div className="cards">{documents.map((document) => (
    <article key={document.arxiv_id}><span className="pill ok">Verified</span><h2>{document.title}</h2>
      <p>arXiv:{document.arxiv_id}v{document.version}</p><p>{document.page_count} pages · indexed corpus</p></article>
  ))}</div>
}

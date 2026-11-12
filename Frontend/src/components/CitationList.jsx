export function CitationList({ citations = [], onSelect }) {
  if (!citations.length) return null
  return <div className="citation-list">{citations.map((citation) => (
    <button className="citation" key={citation.chunk_id} onClick={() => onSelect(citation)}>{citation.paper} · p.{citation.pdf_page}</button>
  ))}</div>
}

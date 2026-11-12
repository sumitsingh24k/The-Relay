export function ChatInput({ busy, onChange, onSend, question }) {
  const onKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); onSend() }
  }
  return (
    <div className="composer">
      <textarea aria-label="Research question" onChange={(event) => onChange(event.target.value)} onKeyDown={onKeyDown}
        placeholder="Ask about the research papers…" value={question} />
      <button disabled={!question.trim() || busy} onClick={onSend}>Send</button>
    </div>
  )
}

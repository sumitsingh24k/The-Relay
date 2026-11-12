import { AnswerPanel } from '../components/AnswerPanel'
import { ChatInput } from '../components/ChatInput'

export function Assistant({ busy, error, messages, onQuestionChange, onSend, onSourceSelect, question, source }) {
  return (
    <section className="assistant">
      <div className="chat">
        {!messages.length && <div className="welcome"><h2>Ask the research library</h2><p>Verified answers from three approved papers.</p></div>}
        {messages.map((message, index) => <AnswerPanel key={`${message.role}-${index}`} message={message} onSourceSelect={onSourceSelect} />)}
        {busy && <article className="message assistant"><b>Relay</b><p>Checking evidence…</p></article>}
        {error && <div className="error">{error}</div>}
        <ChatInput busy={busy} onChange={onQuestionChange} onSend={onSend} question={question} />
      </div>
      <aside className="sources"><h3>Sources context</h3>{source ? <><b>{source.paper}</b><p>arXiv:{source.arxiv_id}v{source.version}</p>
        <p>Page {source.pdf_page}</p><p>{source.section}</p></> : <p>Select a citation to inspect its trusted metadata.</p>}</aside>
    </section>
  )
}

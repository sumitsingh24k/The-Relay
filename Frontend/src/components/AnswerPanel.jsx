import { CitationList } from './CitationList'

export function AnswerPanel({ message, onSourceSelect }) {
  const isUser = message.role === 'user'
  return (
    <article className={`message ${message.role}`}>
      <b>{isUser ? 'You' : 'Relay'}</b><p>{message.text || message.answer}</p>
      {!isUser && <><small>{message.refused ? 'SAFE REFUSAL' : 'VERIFIED EVIDENCE'} · {message.verification?.reason}</small>
        <CitationList citations={message.citations} onSelect={onSourceSelect} /></>}
    </article>
  )
}

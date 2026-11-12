import { useEffect, useState } from 'react'
import { Navbar } from './components/Navbar'
import { StatusBadge } from './components/StatusBadge'
import { Assistant } from './pages/Assistant'
import { Dashboard } from './pages/Dashboard'
import { api } from './services/api'
import './App.css'

const navigation = ['Assistant', 'Documents', 'Performance', 'System Status']

export default function App() {
  const [page, setPage] = useState('Assistant')
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState([])
  const [documents, setDocuments] = useState([])
  const [health, setHealth] = useState(null)
  const [metrics, setMetrics] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [source, setSource] = useState(null)

  const refresh = () => {
    api.health().then(setHealth).catch(() => setHealth({ backend: 'offline' }))
    api.documents().then(({ documents: items }) => setDocuments(items)).catch(() => {})
    api.metrics().then(setMetrics).catch(() => {})
  }

  useEffect(() => { refresh() }, [])

  const startNewChat = () => {
    setMessages([])
    setSource(null)
    setError('')
  }

  async function sendQuestion() {
    if (!question.trim() || busy) return
    const text = question.trim()
    const previousQuestion = messages.filter((message) => message.role === 'user').at(-1)?.text || ''
    setQuestion('')
    setBusy(true)
    setError('')
    setMessages((current) => [...current, { role: 'user', text }])

    try {
      const response = await api.chat(text, previousQuestion)
      setMessages((current) => [...current, { role: 'assistant', ...response }])
      setSource(response.citations?.[0] || null)
      refresh()
    } catch (requestError) {
      setError(requestError.status === 429
        ? 'Provider rate-limited. Please retry after the reset period.'
        : requestError.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="shell">
      <Navbar activePage={page} items={navigation} messages={messages} onNewChat={startNewChat} onNavigate={setPage} />
      <main>
        <header>
          <div><small>RESEARCH WORKSPACE</small><h1>{page}</h1></div>
          <StatusBadge status={health?.backend} />
        </header>
        {page === 'Assistant' ? (
          <Assistant busy={busy} error={error} messages={messages} onQuestionChange={setQuestion} onSend={sendQuestion}
            onSourceSelect={setSource} question={question} source={source} />
        ) : <Dashboard documents={documents} health={health} metrics={metrics} page={page} />}
      </main>
    </div>
  )
}

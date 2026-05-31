import { useState, useRef, useEffect } from 'react'
import { useAuth } from '../../contexts/AuthContext.jsx'
import { EXAMPLE_QUERIES } from '../../constants.js'

function UserMessage({ text }) {
  const { session } = useAuth()
  const initials = (session?.me?.name || session?.username || 'U')
    .split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()
  return (
    <div className="msg user">
      <div className="msg-avatar">{initials}</div>
      <div className="msg-body">
        <div className="msg-bubble">{text}</div>
      </div>
    </div>
  )
}

function ThinkingBubble() {
  return (
    <div className="msg system">
      <div className="msg-avatar" style={{ fontSize: 18 }}>🤖</div>
      <div className="msg-body">
        <div className="thinking">
          <div className="dot-pulse">
            <span /><span /><span />
          </div>
          Retrieving from authorized sources…
        </div>
      </div>
    </div>
  )
}

function ChunkViewer({ chunks }) {
  const [open, setOpen] = useState(false)
  if (!chunks?.length) return null
  return (
    <>
      <button className="chunks-toggle" onClick={() => setOpen(o => !o)}>
        {open ? '▼ Hide' : '▶ Show'} {chunks.length} retrieved chunk{chunks.length > 1 ? 's' : ''}
      </button>
      {open && (
        <div className="chunks-panel">
          {chunks.map((c, i) => (
            <div key={i} className="chunk-card">
              <div className="chunk-header">
                <span className="chunk-source">
                  {c.source_name}
                  <span style={{ color: 'var(--text3)', fontSize: 10 }}> ({c.source_type})</span>
                </span>
                <span className="chunk-score">{(c.relevance_score * 100).toFixed(1)}% match</span>
              </div>
              <div className="chunk-snippet">{c.snippet}</div>
              <div className="chunk-ref">ref: {c.ref}</div>
            </div>
          ))}
        </div>
      )}
    </>
  )
}

function AssistantMessage({ data }) {
  const confClass = {
    High: 'confidence-high', Medium: 'confidence-medium', Low: 'confidence-low',
  }[data.confidence] || 'confidence-low'

  return (
    <div className="msg system">
      <div className="msg-avatar" style={{ fontSize: 18 }}>🤖</div>
      <div className="msg-body" style={{ maxWidth: 720 }}>
        <div className="msg-bubble" style={{ borderTopLeftRadius: 4 }}>
          <div className="msg-answer">{data.answer}</div>
          {data.reasoning && (
            <div className="reasoning-block">💡 {data.reasoning}</div>
          )}
          <div className="msg-meta" style={{ marginTop: 12 }}>
            <span className={`badge ${confClass}`}>◆ {data.confidence} confidence</span>
            <span className="badge info">🔀 {data.total_chunks_retrieved} chunks</span>
            {(data.sources_used || []).map(s => (
              <span key={s} className="badge source">📄 {s}</span>
            ))}
          </div>
          <ChunkViewer chunks={data.retrieved_chunks} />
        </div>
      </div>
    </div>
  )
}

function ErrorMessage({ text }) {
  return (
    <div className="msg system">
      <div className="msg-avatar" style={{ fontSize: 18 }}>🤖</div>
      <div className="msg-body">
        <div className="error-msg">⚠ {text}</div>
      </div>
    </div>
  )
}

export default function QueryPanel() {
  const { session, authFetch } = useAuth()
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [thinking, setThinking] = useState(false)
  const textareaRef = useRef(null)
  const bottomRef = useRef(null)

  const exampleQueries = EXAMPLE_QUERIES[session?.me?.role] || EXAMPLE_QUERIES.default

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, thinking])

  function autoResize() {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 140) + 'px'
  }

  async function sendQuery() {
    if (!session || !input.trim() || thinking) return
    const query = input.trim()
    setInput('')
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
    setMessages(m => [...m, { id: Date.now(), type: 'user', text: query }])
    setThinking(true)
    try {
      const result = await authFetch('/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, k: 5 }),
      })
      setMessages(m => [...m, { id: Date.now() + 1, type: 'assistant', data: result }])
    } catch (e) {
      setMessages(m => [...m, { id: Date.now() + 1, type: 'error', text: e.message }])
    } finally {
      setThinking(false)
    }
  }

  return (
    <div className="panel">
      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="empty-state">
            <div className="empty-icon">🔍</div>
            <div className="empty-title">Ask anything across your data</div>
            <div className="empty-sub">
              Your queries are answered using only sources you're authorized to access.
              All responses include citations and confidence scores.
            </div>
            {session && (
              <div className="example-queries">
                {exampleQueries.map(q => (
                  <div
                    key={q}
                    className="example-q"
                    onClick={() => { setInput(q); textareaRef.current?.focus() }}
                  >
                    {q}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {messages.map(m => {
          if (m.type === 'user')      return <UserMessage      key={m.id} text={m.text} />
          if (m.type === 'assistant') return <AssistantMessage key={m.id} data={m.data} />
          if (m.type === 'error')     return <ErrorMessage     key={m.id} text={m.text} />
          return null
        })}

        {thinking && <ThinkingBubble />}
        <div ref={bottomRef} />
      </div>

      <div className="chat-input-area">
        <div className="chat-input-row">
          <textarea
            ref={textareaRef}
            placeholder="Ask a question across your enterprise data…"
            rows={1}
            value={input}
            disabled={!session}
            onChange={e => { setInput(e.target.value); autoResize() }}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendQuery() } }}
          />
          <button
            className="send-btn"
            onClick={sendQuery}
            disabled={!session || thinking}
            title="Send"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          </button>
        </div>
        <div className="input-hint">
          {session
            ? 'Enter ↵ to send · Shift+Enter for new line'
            : 'Sign in to start querying · Enter ↵ to send'}
        </div>
      </div>

      {!session && (
        <div className="auth-required">
          <div className="auth-required-box">
            <div className="auth-required-icon">🔐</div>
            <div className="auth-required-title">Authentication Required</div>
            <div className="auth-required-sub" style={{ marginTop: 8 }}>
              Sign in with your credentials using the sidebar to query enterprise data.
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

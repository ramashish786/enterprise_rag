import { useState, useEffect } from 'react'
import { useAuth } from './contexts/AuthContext.jsx'
import Sidebar from './components/Sidebar.jsx'
import QueryPanel from './components/panels/QueryPanel.jsx'
import IngestPanel from './components/panels/IngestPanel.jsx'
import DocsPanel from './components/panels/DocsPanel.jsx'
import StatsPanel from './components/panels/StatsPanel.jsx'

const PANEL_TITLES = {
  chat:   'Query Assistant',
  ingest: 'Ingest Document',
  docs:   'Manage Documents',
  stats:  'System Stats',
}

export default function App() {
  const { session, restoring } = useAuth()
  const [panel, setPanel] = useState('chat')
  const [online, setOnline] = useState(false)

  useEffect(() => {
    checkStatus()
    const id = setInterval(checkStatus, 30000)
    return () => clearInterval(id)
  }, [])

  async function checkStatus() {
    try {
      const r = await fetch('/api/v1/health')
      setOnline(r.ok)
    } catch {
      setOnline(false)
    }
  }

  // Avoid flashing the login form while localStorage session is being restored
  if (restoring) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', color: 'var(--text3)', fontFamily: 'var(--mono)', fontSize: 13 }}>
        Loading…
      </div>
    )
  }

  const topbarSub = session
    ? `${session.me?.name} · ${session.me?.role}`
    : 'Secure multi-source retrieval'

  return (
    <div className="shell">
      <Sidebar currentPanel={panel} onPanelChange={setPanel} />

      <main className="main" style={{ position: 'relative' }}>
        <div className="topbar">
          <span className="topbar-title">{PANEL_TITLES[panel]}</span>
          <span className="topbar-sep">·</span>
          <span className="topbar-sub">{topbarSub}</span>
          <div className={`status-dot${online ? '' : ' offline'}`} title="Server status" />
        </div>

        {panel === 'chat'   && <QueryPanel />}
        {panel === 'ingest' && <IngestPanel />}
        {panel === 'docs'   && <DocsPanel />}
        {panel === 'stats'  && <StatsPanel />}
      </main>
    </div>
  )
}

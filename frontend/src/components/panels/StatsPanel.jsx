import { useState, useEffect } from 'react'
import { useAuth } from '../../contexts/AuthContext.jsx'
import { SOURCE_DESC } from '../../constants.js'

export default function StatsPanel() {
  const { session, authFetch } = useAuth()
  const [stats, setStats] = useState(null)

  useEffect(() => { loadStats() }, [])

  async function loadStats() {
    try {
      const data = await authFetch('/stats')
      setStats(data)
    } catch (e) {
      console.warn('Stats error:', e)
    }
  }

  const isAdmin = session?.me?.role === 'admin'
  const sources = stats?.your_allowed_sources || stats?.all_sources || session?.me?.allowed_sources || []

  return (
    <div className="panel">
      <div className="panel-body" style={{ maxWidth: 860 }}>
        <div className="panel-heading">System Stats</div>
        <div className="panel-sub">
          Live view of the indexed knowledge base and access control configuration.
        </div>

        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-label">Total Chunks</div>
            <div className="stat-value">{stats?.total_documents ?? '—'}</div>
            <div className="stat-sub">
              {isAdmin ? 'All indexed chunks' : 'All indexed chunks (system-wide)'}
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Your Role</div>
            <div className="stat-value" style={{ fontSize: 18, paddingTop: 6 }}>
              {session?.me?.role ?? '—'}
            </div>
            <div className="stat-sub">
              {sources.length} {sources.length === 1 ? 'data source' : 'data sources'}
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Collection</div>
            <div className="stat-value" style={{ fontSize: 16, paddingTop: 6, fontFamily: 'var(--mono)' }}>
              {stats?.collection ?? '—'}
            </div>
            <div className="stat-sub">ChromaDB collection</div>
          </div>
        </div>

        <div style={{ marginBottom: 14 }}>
          <div className="sidebar-label" style={{ marginBottom: 12 }}>Your Authorized Sources</div>
          <table className="sources-table">
            <thead>
              <tr><th>Source</th><th>Access</th><th>Description</th></tr>
            </thead>
            <tbody>
              {sources.map(s => (
                <tr key={s}>
                  <td><span className="badge source" style={{ fontSize: 12 }}>📂 {s}</span></td>
                  <td><span className="badge confidence-high" style={{ fontSize: 11 }}>✓ Authorized</span></td>
                  <td style={{ color: 'var(--text2)', fontSize: 13 }}>{SOURCE_DESC[s] || ''}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

import { useAuth } from '../contexts/AuthContext.jsx'
import LoginCard from './LoginCard.jsx'
import UserPill from './UserPill.jsx'
import DemoUsers from './DemoUsers.jsx'

const NAV_ITEMS = [
  { id: 'chat',   icon: '💬', label: 'Query Assistant',  adminOnly: false },
  { id: 'ingest', icon: '📤', label: 'Ingest Document',  adminOnly: true  },
  { id: 'docs',   icon: '🗂️', label: 'Manage Documents', adminOnly: true  },
  { id: 'stats',  icon: '📊', label: 'System Stats',     adminOnly: false },
]

export default function Sidebar({ currentPanel, onPanelChange }) {
  const { session, logout } = useAuth()
  const isAdmin = session?.me?.role === 'admin'

  return (
    <aside className="sidebar">
      <div className="logo">
        <div className="logo-mark">Enterprise <span>RAG</span></div>
        <div className="logo-sub">Intelligence System</div>
      </div>

      {!session ? (
        <>
          <div className="sidebar-section">
            <div className="sidebar-label">Sign In</div>
          </div>
          <LoginCard />
          <div className="sidebar-section" style={{ paddingTop: 8 }}>
            <div className="sidebar-label">Demo Accounts</div>
            <DemoUsers />
          </div>
        </>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', flex: 1 }}>
          <UserPill />
          <div className="sidebar-section">
            <div className="sidebar-label">Navigation</div>
          </div>

          {NAV_ITEMS.filter(n => !n.adminOnly || isAdmin).map(n => (
            <button
              key={n.id}
              className={`nav-item${currentPanel === n.id ? ' active' : ''}`}
              onClick={() => onPanelChange(n.id)}
            >
              <span className="nav-icon">{n.icon}</span>
              {n.label}
            </button>
          ))}

          <div style={{ marginTop: 'auto', padding: 16 }}>
            <button className="btn secondary" style={{ marginTop: 0 }} onClick={logout}>
              Sign out
            </button>
          </div>
        </div>
      )}
    </aside>
  )
}

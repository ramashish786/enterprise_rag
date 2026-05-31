import { useAuth } from '../contexts/AuthContext.jsx'

export default function UserPill() {
  const { session } = useAuth()
  const me = session?.me
  if (!me) return null

  return (
    <div className="user-pill">
      <div className="user-name">{me.name || me.username}</div>
      <div className="user-role">{me.role}</div>
      <div className="user-sources">
        {(me.allowed_sources || []).map(s => (
          <span key={s} className="source-chip">{s}</span>
        ))}
      </div>
    </div>
  )
}

import { useAuth } from '../contexts/AuthContext.jsx'
import { useToast } from '../contexts/ToastContext.jsx'
import { DEMO_USERS } from '../constants.js'

export default function DemoUsers() {
  const { login } = useAuth()
  const toast = useToast()

  async function handleQuickLogin(username, password) {
    try {
      const me = await login(username, password)
      toast(`Welcome, ${me.name || me.username}`, 'success')
    } catch (e) {
      toast('Login failed: ' + e.message, 'error')
    }
  }

  return (
    <div>
      {DEMO_USERS.map(u => (
        <div
          key={u.username}
          className="demo-user"
          onClick={() => handleQuickLogin(u.username, u.password)}
        >
          <div
            className="demo-avatar"
            style={{ background: u.color + '22', color: u.color }}
          >
            {u.emoji}
          </div>
          <div className="demo-info">
            <div className="demo-username">{u.username}</div>
            <div className="demo-role-badge">{u.role}</div>
          </div>
        </div>
      ))}
    </div>
  )
}

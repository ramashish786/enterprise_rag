import { useState } from 'react'
import { useAuth } from '../contexts/AuthContext.jsx'
import { useToast } from '../contexts/ToastContext.jsx'

export default function LoginCard() {
  const { login } = useAuth()
  const toast = useToast()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleLogin() {
    if (!username.trim() || !password.trim()) {
      toast('Enter username and password', 'error')
      return
    }
    setLoading(true)
    try {
      const me = await login(username, password)
      toast(`Welcome, ${me.name || me.username}`, 'success')
    } catch (e) {
      toast('Login failed: ' + e.message, 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-card">
      <input
        type="text"
        placeholder="Username"
        autoComplete="username"
        value={username}
        onChange={e => setUsername(e.target.value)}
      />
      <input
        type="password"
        placeholder="Password"
        autoComplete="current-password"
        value={password}
        onChange={e => setPassword(e.target.value)}
        onKeyDown={e => e.key === 'Enter' && handleLogin()}
      />
      <button className="btn" onClick={handleLogin} disabled={loading}>
        {loading ? 'Connecting…' : 'Connect'}
      </button>
    </div>
  )
}

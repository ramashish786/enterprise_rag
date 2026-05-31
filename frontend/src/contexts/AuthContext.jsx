import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { apiFetch } from '../api.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [session, setSession] = useState(null)
  const [restoring, setRestoring] = useState(true)

  // Restore session from localStorage on page load
  useEffect(() => {
    const saved = localStorage.getItem('rag_session')
    if (!saved) { setRestoring(false); return }
    const { username, password } = JSON.parse(saved)
    apiFetch('/me', { username, password })
      .then(me => setSession({ username, password, me }))
      .catch(() => localStorage.removeItem('rag_session'))
      .finally(() => setRestoring(false))
  }, [])

  const login = useCallback(async (username, password) => {
    const me = await apiFetch('/me', { username, password })
    setSession({ username, password, me })
    localStorage.setItem('rag_session', JSON.stringify({ username, password }))
    return me
  }, [])

  const logout = useCallback(() => {
    setSession(null)
    localStorage.removeItem('rag_session')
  }, [])

  // Pre-bound fetch helper — components call authFetch('/endpoint') without managing auth headers
  const authFetch = useCallback(
    (path, opts = {}) => apiFetch(path, { username: session?.username, password: session?.password, ...opts }),
    [session],
  )

  return (
    <AuthContext.Provider value={{ session, restoring, login, logout, authFetch }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)

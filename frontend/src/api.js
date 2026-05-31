// All paths are relative so they work both when served by FastAPI (/api/v1/...)
// and when using the Vite dev server (proxied to http://localhost:8000).
export const API_BASE = '/api/v1'

export async function apiFetch(path, { username, password, ...opts } = {}) {
  const headers = { ...(opts.headers || {}) }
  if (username && password) {
    headers['Authorization'] = 'Basic ' + btoa(`${username}:${password}`)
  }
  const res = await fetch(API_BASE + path, { ...opts, headers })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || res.statusText)
  }
  return res.json()
}

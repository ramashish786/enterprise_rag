import { useState, useEffect } from 'react'
import { useAuth } from '../../contexts/AuthContext.jsx'
import { useToast } from '../../contexts/ToastContext.jsx'

export default function DocsPanel() {
  const { authFetch } = useAuth()
  const toast = useToast()
  const [docs, setDocs] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => { loadDocuments() }, [])

  async function loadDocuments() {
    setLoading(true)
    try {
      const data = await authFetch('/documents')
      setDocs(data.documents || [])
    } catch (e) {
      toast('Failed to load documents: ' + e.message, 'error')
    } finally {
      setLoading(false)
    }
  }

  async function deleteDocument(sourceName) {
    if (!confirm(`Delete all chunks from "${sourceName}"?\n\nThis cannot be undone.`)) return
    try {
      const data = await authFetch(`/documents/${encodeURIComponent(sourceName)}`, { method: 'DELETE' })
      toast(`Deleted ${data.chunks_deleted} chunks from "${data.source_name}"`, 'success')
      loadDocuments()
    } catch (e) {
      toast('Delete failed: ' + e.message, 'error')
    }
  }

  return (
    <div className="panel">
      <div className="panel-body" style={{ maxWidth: 860 }}>
        <div className="panel-heading">Manage Documents</div>
        <div className="panel-sub">
          View and delete documents indexed in the knowledge base. Admin access required.
        </div>

        <button
          className="btn"
          style={{ width: 'auto', padding: '9px 24px', marginBottom: 24 }}
          onClick={loadDocuments}
          disabled={loading}
        >
          {loading ? 'Loading…' : 'Refresh'}
        </button>

        {!loading && docs.length === 0 && (
          <div style={{ color: 'var(--text3)', fontSize: 13 }}>No documents indexed yet.</div>
        )}

        {docs.length > 0 && (
          <table className="sources-table">
            <thead>
              <tr>
                <th>Document</th>
                <th>Source Type</th>
                <th style={{ textAlign: 'right' }}>Chunks</th>
                <th style={{ textAlign: 'right' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {docs.map(d => (
                <tr key={d.source_name}>
                  <td style={{ fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--accent)' }}>
                    {d.source_name}
                  </td>
                  <td>
                    <span className="badge source" style={{ fontSize: 11 }}>📂 {d.source_type}</span>
                  </td>
                  <td style={{ fontFamily: 'var(--mono)', color: 'var(--text2)', textAlign: 'right' }}>
                    {d.chunk_count}
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <button
                      className="btn danger"
                      style={{ width: 'auto', padding: '4px 14px', fontSize: 12, marginTop: 0 }}
                      onClick={() => deleteDocument(d.source_name)}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

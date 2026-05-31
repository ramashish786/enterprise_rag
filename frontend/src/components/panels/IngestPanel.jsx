import { useState, useRef } from 'react'
import { useAuth } from '../../contexts/AuthContext.jsx'
import { useToast } from '../../contexts/ToastContext.jsx'
import { apiFetch } from '../../api.js'

const SOURCE_TYPES = [
  { value: 'finance_reports',  label: 'Finance Reports'  },
  { value: 'hr_records',       label: 'HR Records'       },
  { value: 'engineering_docs', label: 'Engineering Docs' },
  { value: 'legal_contracts',  label: 'Legal Contracts'  },
  { value: 'sales_data',       label: 'Sales Data'       },
  { value: 'compliance',       label: 'Compliance'       },
  { value: 'operational',      label: 'Operational'      },
  { value: 'public',           label: 'Public'           },
]

function formatBytes(b) {
  if (b < 1024) return b + ' B'
  if (b < 1024 * 1024) return (b / 1024).toFixed(1) + ' KB'
  return (b / 1024 / 1024).toFixed(1) + ' MB'
}

export default function IngestPanel() {
  const { session } = useAuth()
  const toast = useToast()
  const [sourceType, setSourceType] = useState('finance_reports')
  const [file, setFile] = useState(null)
  const [dragging, setDragging] = useState(false)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const fileInputRef = useRef(null)

  function pickFile(f) { setFile(f); setResult(null) }
  function clearFile() { setFile(null); setResult(null); if (fileInputRef.current) fileInputRef.current.value = '' }

  async function doIngest() {
    if (!file) { toast('Select a file first', 'error'); return }
    setLoading(true)
    setResult(null)
    const formData = new FormData()
    formData.append('file', file)
    formData.append('source_type', sourceType)
    try {
      const data = await apiFetch('/ingest', {
        username: session.username,
        password: session.password,
        method: 'POST',
        body: formData,
      })
      setResult({ ok: true, msg: `✓ Indexed ${data.chunks_indexed} chunks from ${data.file} into ${data.source_type}` })
      toast('Document indexed successfully', 'success')
      clearFile()
    } catch (e) {
      setResult({ ok: false, msg: '✗ ' + e.message })
      toast('Ingest failed', 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="panel">
      <div className="panel-body">
        <div className="panel-heading">Ingest Document</div>
        <div className="panel-sub">
          Upload a file to index into the enterprise knowledge base. Admin access required.
        </div>

        <div className="form-group">
          <label className="form-label">Data Source Type</label>
          <select
            className="form-select"
            value={sourceType}
            onChange={e => setSourceType(e.target.value)}
          >
            {SOURCE_TYPES.map(s => (
              <option key={s.value} value={s.value}>{s.label}</option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label className="form-label">File</label>
          {!file ? (
            <div
              className={`dropzone${dragging ? ' drag' : ''}`}
              onClick={() => fileInputRef.current?.click()}
              onDragOver={e => { e.preventDefault(); setDragging(true) }}
              onDragLeave={() => setDragging(false)}
              onDrop={e => { e.preventDefault(); setDragging(false); const f = e.dataTransfer.files[0]; if (f) pickFile(f) }}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.csv,.json,.jsonl,.txt,.md"
                style={{ display: 'none' }}
                onChange={e => { const f = e.target.files[0]; if (f) pickFile(f) }}
              />
              <div className="dropzone-icon">📁</div>
              <div className="dropzone-text">Drop file here or click to browse</div>
              <div className="dropzone-hint">PDF · CSV · JSON · JSONL · TXT · MD</div>
            </div>
          ) : (
            <div className="file-selected">
              <span style={{ fontSize: 18 }}>📄</span>
              <span className="file-name">{file.name}</span>
              <span className="file-size">{formatBytes(file.size)}</span>
              <button
                onClick={clearFile}
                style={{ background: 'none', border: 'none', color: 'var(--text3)', cursor: 'pointer', fontSize: 16 }}
                title="Remove"
              >✕</button>
            </div>
          )}
        </div>

        <button
          className="btn"
          style={{ width: 'auto', padding: '9px 24px' }}
          onClick={doIngest}
          disabled={loading}
        >
          {loading ? 'Uploading…' : 'Upload & Index'}
        </button>

        {result && (
          <div className={`ingest-result ${result.ok ? 'success' : 'error'}`}>
            {result.msg}
          </div>
        )}
      </div>
    </div>
  )
}

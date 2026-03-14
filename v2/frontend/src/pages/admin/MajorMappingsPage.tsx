import { FormEvent, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'

import { API_BASE_URL } from '../../lib/api'
import { useMajorMappings, useMajors } from '../../lib/hooks'

const FIELD_LABEL: React.CSSProperties = {
  display: 'block',
  fontSize: '0.72rem',
  fontWeight: 700,
  color: 'var(--muted)',
  marginBottom: '4px',
  textTransform: 'uppercase',
}

function authedFetch(path: string, init?: RequestInit) {
  const token = window.localStorage.getItem('advising_v2_token')
  return fetch(`${API_BASE_URL}/api${path}`, {
    ...init,
    headers: {
      ...(init?.headers || {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  })
}

const EMPTY_FORM = { file_code: '', major_id: '', id_year_min: '', id_year_max: '' }

export function MajorMappingsPage() {
  const queryClient = useQueryClient()
  const mappings = useMajorMappings()
  const majors = useMajors()
  const [form, setForm] = useState(EMPTY_FORM)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [deletingId, setDeletingId] = useState<number | null>(null)

  async function handleAdd(e: FormEvent) {
    e.preventDefault()
    if (!form.file_code.trim() || !form.major_id) {
      setMessage({ type: 'error', text: 'File code and target major are required.' })
      return
    }
    const body = {
      file_code: form.file_code.trim().toUpperCase(),
      major_id: Number(form.major_id),
      id_year_min: form.id_year_min ? Number(form.id_year_min) : null,
      id_year_max: form.id_year_max ? Number(form.id_year_max) : null,
    }
    const res = await authedFetch('/major-mappings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (!res.ok) {
      setMessage({ type: 'error', text: await res.text() })
      return
    }
    setMessage({ type: 'success', text: 'Mapping rule added.' })
    setForm(EMPTY_FORM)
    queryClient.invalidateQueries({ queryKey: ['major-mappings'] })
  }

  async function handleDelete(id: number) {
    setDeletingId(id)
    const res = await authedFetch(`/major-mappings/${id}`, { method: 'DELETE' })
    setDeletingId(null)
    if (!res.ok) {
      setMessage({ type: 'error', text: await res.text() })
      return
    }
    queryClient.invalidateQueries({ queryKey: ['major-mappings'] })
  }

  return (
    <section className="stack" style={{ maxWidth: '900px', margin: '0 auto' }}>
      <div className="page-header mb-4">
        <div>
          <div className="eyebrow text-muted">Admin Panel</div>
          <h2>Major Code Mapping</h2>
          <p className="text-muted" style={{ margin: '4px 0 0' }}>
            Maps the MAJOR column value in uploaded progress files to DB majors.
            Use multiple rules for the same file code to split by degree plan based on student ID year.
          </p>
        </div>
      </div>

      {message && (
        <div className={`alert mb-4 ${message.type === 'error' ? 'alert-error' : 'alert-success'}`}>
          {message.text}
          <button type="button" className="close-btn" onClick={() => setMessage(null)}>&times;</button>
        </div>
      )}

      {/* Add rule form */}
      <form className="panel stack mb-6" onSubmit={handleAdd}>
        <h3 style={{ margin: 0, marginBottom: '0.75rem' }}>Add Mapping Rule</h3>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '0.75rem', alignItems: 'end' }}>
          <div>
            <label style={FIELD_LABEL}>File Code</label>
            <input
              required
              value={form.file_code}
              onChange={e => setForm({ ...form, file_code: e.target.value })}
              placeholder="e.g. SPETHE"
              style={{ textTransform: 'uppercase' }}
            />
          </div>
          <div>
            <label style={FIELD_LABEL}>Maps To Major</label>
            <select
              required
              className="select-input"
              value={form.major_id}
              onChange={e => setForm({ ...form, major_id: e.target.value })}
            >
              <option value="">Select major…</option>
              {majors.data?.map(m => (
                <option key={m.id} value={m.id}>{m.code} — {m.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label style={FIELD_LABEL}>ID Year Min</label>
            <input
              type="number"
              value={form.id_year_min}
              onChange={e => setForm({ ...form, id_year_min: e.target.value })}
              placeholder="e.g. 2022"
              min={2000}
              max={2100}
            />
          </div>
          <div>
            <label style={FIELD_LABEL}>ID Year Max</label>
            <input
              type="number"
              value={form.id_year_max}
              onChange={e => setForm({ ...form, id_year_max: e.target.value })}
              placeholder="e.g. 2021"
              min={2000}
              max={2100}
            />
          </div>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}>
          <button type="submit" className="btn-primary">Add Rule</button>
          {(form.file_code || form.major_id || form.id_year_min || form.id_year_max) && (
            <button type="button" className="btn-outline" onClick={() => setForm(EMPTY_FORM)}>Clear</button>
          )}
        </div>
      </form>

      {/* Rules table */}
      <div className="panel">
        <h3 style={{ margin: '0 0 1rem' }}>Configured Rules</h3>
        {mappings.isLoading && <p className="text-muted">Loading…</p>}
        {mappings.data && mappings.data.length === 0 && (
          <p className="text-muted">No mapping rules configured yet. Add rules above to enable multi-major progress uploads.</p>
        )}
        {mappings.data && mappings.data.length > 0 && (
          <table className="data-table" style={{ width: '100%' }}>
            <thead>
              <tr>
                <th>File Code</th>
                <th>Maps To Major</th>
                <th>ID Year Min</th>
                <th>ID Year Max</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {mappings.data.map(m => (
                <tr key={m.id}>
                  <td><code>{m.file_code}</code></td>
                  <td>
                    <strong>{m.major_code}</strong>
                    <span className="text-muted" style={{ marginLeft: '0.4rem', fontSize: '0.85em' }}>{m.major_name}</span>
                  </td>
                  <td>{m.id_year_min ?? <span className="text-muted">—</span>}</td>
                  <td>{m.id_year_max ?? <span className="text-muted">—</span>}</td>
                  <td style={{ textAlign: 'right' }}>
                    <button
                      type="button"
                      className="btn-outline btn-sm"
                      disabled={deletingId === m.id}
                      onClick={() => handleDelete(m.id)}
                    >
                      {deletingId === m.id ? '…' : 'Delete'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="panel" style={{ background: 'var(--surface-2, var(--surface))' }}>
        <h4 style={{ margin: '0 0 0.5rem' }}>How it works</h4>
        <ul style={{ margin: 0, paddingLeft: '1.25rem', fontSize: '0.85rem', color: 'var(--muted)', lineHeight: 1.6 }}>
          <li>Upload a progress file using <strong>Auto (All Majors)</strong> in the Datasets page.</li>
          <li>Each student's <code>MAJOR</code> column value is matched against the File Code here.</li>
          <li>If ID Year Min / Max are set, the first 4 digits of the student ID are compared to the range.</li>
          <li>Multiple rules for the same File Code allow splitting by degree plan year (e.g. old vs new curriculum).</li>
          <li>Students whose MAJOR value has no matching rule will be skipped.</li>
        </ul>
      </div>
    </section>
  )
}

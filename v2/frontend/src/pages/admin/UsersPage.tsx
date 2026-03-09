import { FormEvent, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'

import { API_BASE_URL } from '../../lib/api'
import { useMajors, useUsers } from '../../lib/hooks'

async function authedPatch(path: string) {
  const token = window.localStorage.getItem('advising_v2_token')
  return fetch(`${API_BASE_URL}/api${path}`, {
    method: 'PATCH',
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  })
}

export function UsersPage() {
  const queryClient = useQueryClient()
  const majors = useMajors()
  const users = useUsers()
  const [payload, setPayload] = useState({ email: '', full_name: '', password: '', role: 'adviser', major_codes: ['PBHL'] })
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    const token = window.localStorage.getItem('advising_v2_token')
    const res = await fetch(`${API_BASE_URL}/api/users`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: JSON.stringify(payload),
    })
    if (!res.ok) { setMessage({ type: 'error', text: await res.text() }); return }
    setMessage({ type: 'success', text: `User ${payload.full_name} created.` })
    setPayload({ email: '', full_name: '', password: '', role: 'adviser', major_codes: ['PBHL'] })
    queryClient.invalidateQueries({ queryKey: ['users'] })
  }

  async function handleToggle(userId: number, isActive: boolean) {
    const action = isActive ? 'deactivate' : 'activate'
    const res = await authedPatch(`/users/${userId}/${action}`)
    if (!res.ok) { setMessage({ type: 'error', text: await res.text() }); return }
    setMessage({ type: 'success', text: `User ${action}d.` })
    queryClient.invalidateQueries({ queryKey: ['users'] })
  }

  return (
    <section className="stack" style={{ maxWidth: '900px', margin: '0 auto' }}>
      <div className="page-header mb-4">
        <div>
          <div className="eyebrow text-muted">Admin Panel</div>
          <h2>Users &amp; Access</h2>
        </div>
      </div>

      {message && (
        <div className={`alert mb-4 ${message.type === 'error' ? 'alert-error' : 'alert-success'}`}>
          {message.text}
          <button type="button" className="close-btn" onClick={() => setMessage(null)}>&times;</button>
        </div>
      )}

      {/* Create user form */}
      <form className="panel stack mb-6" onSubmit={handleSubmit}>
        <h3 style={{ margin: 0, marginBottom: '0.75rem' }}>Create New User</h3>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', marginBottom: '0.75rem' }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: 700, color: 'var(--muted)', marginBottom: '4px', textTransform: 'uppercase' }}>Full Name</label>
            <input required value={payload.full_name} onChange={e => setPayload({ ...payload, full_name: e.target.value })} placeholder="Dr. Jane Smith" />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: 700, color: 'var(--muted)', marginBottom: '4px', textTransform: 'uppercase' }}>Email</label>
            <input required type="email" value={payload.email} onChange={e => setPayload({ ...payload, email: e.target.value })} placeholder="jsmith@example.com" />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: 700, color: 'var(--muted)', marginBottom: '4px', textTransform: 'uppercase' }}>Password</label>
            <input required type="password" value={payload.password} onChange={e => setPayload({ ...payload, password: e.target.value })} placeholder="Temporary password" />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: 700, color: 'var(--muted)', marginBottom: '4px', textTransform: 'uppercase' }}>Role</label>
            <select className="select-input" value={payload.role} onChange={e => setPayload({ ...payload, role: e.target.value })}>
              <option value="admin">Admin</option>
              <option value="adviser">Adviser</option>
            </select>
          </div>
        </div>
        <div style={{ marginBottom: '0.75rem' }}>
          <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: 700, color: 'var(--muted)', marginBottom: '4px', textTransform: 'uppercase' }}>Major Access</label>
          <select className="select-input" value={payload.major_codes[0]} onChange={e => setPayload({ ...payload, major_codes: [e.target.value] })}>
            {majors.data?.map(m => <option key={m.code} value={m.code}>{m.code} — {m.name}</option>)}
          </select>
        </div>
        <button type="submit" className="btn-primary btn-sm" style={{ alignSelf: 'flex-start' }}>Create User</button>
      </form>

      {/* Users table */}
      <div className="panel">
        <h3 style={{ margin: '0 0 1rem' }}>All Users</h3>
        {users.data?.length === 0 ? (
          <p className="text-muted text-sm" style={{ textAlign: 'center', padding: '2rem' }}>No users yet.</p>
        ) : (
          <table className="premium-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Role</th>
                <th>Created</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {users.data?.map(u => (
                <tr key={u.id} style={{ opacity: u.is_active ? 1 : 0.55 }}>
                  <td style={{ fontWeight: 600, fontSize: '0.875rem' }}>{u.full_name}</td>
                  <td style={{ fontSize: '0.8rem', color: 'var(--muted)', fontFamily: 'monospace' }}>{u.email}</td>
                  <td>
                    <span style={{ fontSize: '0.7rem', padding: '2px 8px', borderRadius: '4px', fontWeight: 600, background: u.role === 'admin' ? '#fdf4ff' : '#eff6ff', color: u.role === 'admin' ? '#7e22ce' : '#1d4ed8' }}>
                      {u.role}
                    </span>
                  </td>
                  <td style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>{new Date(u.created_at).toLocaleDateString()}</td>
                  <td>
                    <span style={{ fontSize: '0.7rem', padding: '2px 8px', borderRadius: '4px', fontWeight: 600, background: u.is_active ? '#f0fdf4' : '#f1f5f9', color: u.is_active ? '#15803d' : '#94a3b8' }}>
                      {u.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <button
                      type="button"
                      className="btn-sm btn-outline"
                      style={{ fontSize: '0.75rem', color: u.is_active ? '#dc2626' : '#15803d', borderColor: u.is_active ? '#fecaca' : '#bbf7d0' }}
                      onClick={() => handleToggle(u.id, u.is_active)}
                    >
                      {u.is_active ? 'Deactivate' : 'Reactivate'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  )
}

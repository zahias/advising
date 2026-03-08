import { FormEvent, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'

import { API_BASE_URL } from '../../lib/api'
import { useMajors, useUsers } from '../../lib/hooks'

export function UsersPage() {
  const queryClient = useQueryClient()
  const majors = useMajors()
  const users = useUsers()
  const [payload, setPayload] = useState({ email: '', full_name: '', password: '', role: 'adviser', major_codes: ['PBHL'] })
  const [message, setMessage] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    const token = window.localStorage.getItem('advising_v2_token')
    const response = await fetch(`${API_BASE_URL}/api/users`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: JSON.stringify(payload),
    })
    setMessage(response.ok ? 'User created.' : await response.text())
    queryClient.invalidateQueries({ queryKey: ['users'] })
  }

  return (
    <section className="stack">
      <div className="page-header"><div><div className="eyebrow">Admin Panel</div><h2>Users and Access</h2></div></div>
      <form className="panel stack" onSubmit={handleSubmit}>
        <div className="field-row">
          <label><span>Full name</span><input value={payload.full_name} onChange={(event) => setPayload({ ...payload, full_name: event.target.value })} /></label>
          <label><span>Email</span><input value={payload.email} onChange={(event) => setPayload({ ...payload, email: event.target.value })} /></label>
          <label><span>Password</span><input value={payload.password} onChange={(event) => setPayload({ ...payload, password: event.target.value })} /></label>
          <label><span>Role</span><select value={payload.role} onChange={(event) => setPayload({ ...payload, role: event.target.value })}><option value="admin">Admin</option><option value="adviser">Adviser</option></select></label>
        </div>
        <label><span>Major access</span><select value={payload.major_codes[0]} onChange={(event) => setPayload({ ...payload, major_codes: [event.target.value] })}>{majors.data?.map((major) => <option key={major.code} value={major.code}>{major.code}</option>)}</select></label>
        <button type="submit">Create user</button>
        {message ? <div className="alert">{message}</div> : null}
      </form>
      <div className="panel"><table><thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Status</th></tr></thead><tbody>{users.data?.map((user) => <tr key={user.id}><td>{user.full_name}</td><td>{user.email}</td><td>{user.role}</td><td>{user.is_active ? 'Active' : 'Inactive'}</td></tr>)}</tbody></table></div>
    </section>
  )
}

import { useState } from 'react'

import { API_BASE_URL } from '../../lib/api'

export function ImportsPage() {
  const [majorCode, setMajorCode] = useState('PBHL')
  const [message, setMessage] = useState<string | null>(null)

  async function handleImport() {
    const token = window.localStorage.getItem('advising_v2_token')
    const response = await fetch(`${API_BASE_URL}/api/imports/legacy/${majorCode}`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    })
    setMessage(response.ok ? JSON.stringify(await response.json(), null, 2) : await response.text())
  }

  return (
    <section className="stack">
      <div className="page-header"><div><div className="eyebrow">Admin Panel</div><h2>Legacy Imports</h2></div></div>
      <div className="panel stack">
        <label><span>Major code</span><input value={majorCode} onChange={(event) => setMajorCode(event.target.value)} /></label>
        <button type="button" onClick={handleImport}>Import frozen legacy snapshot</button>
        {message ? <pre className="code-block">{message}</pre> : null}
      </div>
    </section>
  )
}

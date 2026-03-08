import { FormEvent, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'

import { API_BASE_URL } from '../../lib/api'
import { useTemplates } from '../../lib/hooks'

export function TemplatesPage() {
  const queryClient = useQueryClient()
  const templates = useTemplates()
  const [payload, setPayload] = useState({ major_code: 'PBHL', template_key: 'default', display_name: 'Standard Advising', description: '', subject_template: 'Academic Advising - {major}', body_template: 'Dear {student_name},', include_summary: true })
  const [message, setMessage] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    const token = window.localStorage.getItem('advising_v2_token')
    const response = await fetch(`${API_BASE_URL}/api/templates`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: JSON.stringify(payload),
    })
    setMessage(response.ok ? 'Template saved.' : await response.text())
    queryClient.invalidateQueries({ queryKey: ['templates'] })
  }

  return (
    <section className="stack">
      <div className="page-header"><div><div className="eyebrow">Admin Panel</div><h2>Email Templates</h2></div></div>
      <form className="panel stack" onSubmit={handleSubmit}>
        <div className="field-row"><label><span>Major code</span><input value={payload.major_code ?? ''} onChange={(event) => setPayload({ ...payload, major_code: event.target.value })} /></label><label><span>Template key</span><input value={payload.template_key} onChange={(event) => setPayload({ ...payload, template_key: event.target.value })} /></label><label><span>Display name</span><input value={payload.display_name} onChange={(event) => setPayload({ ...payload, display_name: event.target.value })} /></label></div>
        <label><span>Subject</span><input value={payload.subject_template} onChange={(event) => setPayload({ ...payload, subject_template: event.target.value })} /></label>
        <label><span>Body</span><textarea rows={8} value={payload.body_template} onChange={(event) => setPayload({ ...payload, body_template: event.target.value })} /></label>
        <button type="submit">Save template</button>
        {message ? <div className="alert">{message}</div> : null}
      </form>
      <div className="panel"><table><thead><tr><th>Key</th><th>Name</th><th>Scope</th></tr></thead><tbody>{templates.data?.map((template) => <tr key={template.id}><td>{template.template_key}</td><td>{template.display_name}</td><td>{template.major_id ? 'Major-specific' : 'Global'}</td></tr>)}</tbody></table></div>
    </section>
  )
}

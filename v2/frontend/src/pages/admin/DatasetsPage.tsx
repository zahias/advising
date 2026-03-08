import { FormEvent, useMemo, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'

import { API_BASE_URL } from '../../lib/api'
import { useDatasetVersions, useMajors } from '../../lib/hooks'

const datasetTypes = ['courses', 'progress', 'advising_selections', 'email_roster']

export function DatasetsPage() {
  const queryClient = useQueryClient()
  const majors = useMajors()
  const [majorCode, setMajorCode] = useState('PBHL')
  const [datasetType, setDatasetType] = useState('courses')
  const [file, setFile] = useState<File | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const versions = useDatasetVersions(majorCode)

  async function handleUpload(event: FormEvent) {
    event.preventDefault()
    if (!file) return
    const token = window.localStorage.getItem('advising_v2_token')
    const formData = new FormData()
    formData.append('major_code', majorCode)
    formData.append('dataset_type', datasetType)
    formData.append('file', file)
    const response = await fetch(`${API_BASE_URL}/api/datasets/upload`, {
      method: 'POST',
      body: formData,
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    })
    if (!response.ok) {
      setMessage(await response.text())
      return
    }
    setMessage('Dataset uploaded.')
    setFile(null)
    queryClient.invalidateQueries({ queryKey: ['dataset-versions', majorCode] })
  }

  return (
    <section className="stack">
      <div className="page-header"><div><div className="eyebrow">Admin Panel</div><h2>Datasets</h2></div></div>
      <form className="panel stack" onSubmit={handleUpload}>
        <div className="field-row">
          <label><span>Major</span><select value={majorCode} onChange={(event) => setMajorCode(event.target.value)}>{majors.data?.map((major) => <option key={major.code} value={major.code}>{major.code}</option>)}</select></label>
          <label><span>Dataset type</span><select value={datasetType} onChange={(event) => setDatasetType(event.target.value)}>{datasetTypes.map((item) => <option key={item}>{item}</option>)}</select></label>
          <label><span>File</span><input type="file" onChange={(event) => setFile(event.target.files?.[0] || null)} /></label>
        </div>
        <button type="submit">Upload dataset</button>
        {message ? <div className="alert">{message}</div> : null}
      </form>
      <div className="panel">
        <h3>Version history</h3>
        <table><thead><tr><th>Type</th><th>Label</th><th>Filename</th><th>Created</th></tr></thead><tbody>{versions.data?.map((version) => <tr key={version.id}><td>{version.dataset_type}</td><td>{version.version_label}</td><td>{version.original_filename}</td><td>{new Date(version.created_at).toLocaleString()}</td></tr>)}</tbody></table>
      </div>
    </section>
  )
}

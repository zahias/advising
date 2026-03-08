import { useBackups } from '../../lib/hooks'

export function BackupsPage() {
  const backups = useBackups()
  return (
    <section className="stack">
      <div className="page-header"><div><div className="eyebrow">Admin Panel</div><h2>Backups</h2></div></div>
      <div className="panel"><table><thead><tr><th>ID</th><th>Status</th><th>Created</th><th>Storage key</th></tr></thead><tbody>{backups.data?.map((backup) => <tr key={backup.id}><td>{backup.id}</td><td>{backup.status}</td><td>{new Date(backup.created_at).toLocaleString()}</td><td>{backup.storage_key || '—'}</td></tr>)}</tbody></table></div>
    </section>
  )
}

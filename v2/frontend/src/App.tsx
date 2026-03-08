import type { ReactElement } from 'react'
import { Navigate, Outlet, Route, Routes } from 'react-router-dom'

import { AppFrame } from './components/AppFrame'
import { useCurrentUser } from './lib/hooks'
import { LoginPage } from './pages/LoginPage'
import { AdminOverviewPage } from './pages/admin/AdminOverviewPage'
import { BackupsPage } from './pages/admin/BackupsPage'
import { DatasetsPage } from './pages/admin/DatasetsPage'
import { ImportsPage } from './pages/admin/ImportsPage'
import { PeriodsPage } from './pages/admin/PeriodsPage'
import { TemplatesPage } from './pages/admin/TemplatesPage'
import { UsersPage } from './pages/admin/UsersPage'
import { DashboardPage } from './pages/adviser/DashboardPage'
import { AdviserSettingsPage } from './pages/adviser/AdviserSettingsPage'
import { InsightsPage } from './pages/adviser/InsightsPage'
import { WorkspacePage } from './pages/adviser/WorkspacePage'

function RequireRole({ role, children }: { role: 'admin' | 'adviser'; children: ReactElement }) {
  const currentUser = useCurrentUser()
  if (!currentUser.data) return <LoginPage />
  if (currentUser.data.role !== role) {
    return <Navigate to={currentUser.data.role === 'admin' ? '/admin' : '/adviser'} replace />
  }
  return children
}

function AdminLayout() {
  const { data: user } = useCurrentUser()
  if (!user) return null
  return (
    <AppFrame
      title="Admin Control"
      subtitle="Datasets, users, periods, templates, imports, and backups."
      user={user}
      items={[
        { to: '/admin', label: 'Overview' },
        { to: '/admin/datasets', label: 'Datasets' },
        { to: '/admin/periods', label: 'Periods' },
        { to: '/admin/users', label: 'Users' },
        { to: '/admin/templates', label: 'Templates' },
        { to: '/admin/imports', label: 'Imports' },
        { to: '/admin/backups', label: 'Backups' },
      ]}
    >
      <Outlet />
    </AppFrame>
  )
}

function AdviserLayout() {
  const { data: user } = useCurrentUser()
  if (!user) return null
  return (
    <AppFrame
      title="Adviser Workspace"
      subtitle="Dashboard, advising flows, and insight tooling for assigned majors."
      user={user}
      items={[
        { to: '/adviser', label: 'Dashboard' },
        { to: '/adviser/workspace', label: 'Workspace' },
        { to: '/adviser/insights', label: 'Insights' },
        { to: '/adviser/settings', label: 'Settings' },
      ]}
    >
      <Outlet />
    </AppFrame>
  )
}

export default function App() {
  const token = window.localStorage.getItem('advising_v2_token')
  const currentUser = useCurrentUser()

  if (!token) return <LoginPage />
  if (currentUser.isLoading) return <div className="loading-screen">Loading…</div>
  if (currentUser.isError || !currentUser.data) return <LoginPage />

  return (
    <Routes>
      <Route path="/" element={<Navigate to={currentUser.data.role === 'admin' ? '/admin' : '/adviser'} replace />} />
      <Route path="/admin" element={<RequireRole role="admin"><AdminLayout /></RequireRole>}>
        <Route index element={<AdminOverviewPage />} />
        <Route path="datasets" element={<DatasetsPage />} />
        <Route path="periods" element={<PeriodsPage />} />
        <Route path="users" element={<UsersPage />} />
        <Route path="templates" element={<TemplatesPage />} />
        <Route path="imports" element={<ImportsPage />} />
        <Route path="backups" element={<BackupsPage />} />
      </Route>
      <Route path="/adviser" element={<RequireRole role="adviser"><AdviserLayout /></RequireRole>}>
        <Route index element={<DashboardPage />} />
        <Route path="workspace" element={<WorkspacePage />} />
        <Route path="insights" element={<InsightsPage />} />
        <Route path="settings" element={<AdviserSettingsPage />} />
      </Route>
    </Routes>
  )
}

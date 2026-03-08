import { NavLink } from 'react-router-dom'
import type { PropsWithChildren } from 'react'

import type { CurrentUser } from '../lib/api'

export function AppFrame({ title, subtitle, user, items, children }: PropsWithChildren<{ title: string; subtitle: string; user: CurrentUser; items: { to: string; label: string }[] }>) {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div>
          <div className="eyebrow">Advising V2</div>
          <h1>{title}</h1>
          <p>{subtitle}</p>
        </div>
        <nav className="nav-list">
          {items.map((item) => (
            <NavLink key={item.to} to={item.to} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="profile-card">
          <div className="profile-role">{user.role}</div>
          <strong>{user.full_name}</strong>
          <span>{user.email}</span>
        </div>
      </aside>
      <main className="content">{children}</main>
    </div>
  )
}

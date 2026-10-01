import { useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { useCoreData, dateLabel } from '../services/coreService.js';
import { ROLE_LABEL } from '../services/adminService.js';
import PageHeader from '../components/layout/PageHeader.jsx';
import { Card, CardHeader } from '../components/ui/Card.jsx';
import Button from '../components/ui/Button.jsx';
import { EmptyState } from '../components/ui/States.jsx';
import { MetricTile, RoleBadge } from '../components/admin/AdminUi.jsx';

const ROLES = ['student', 'staff', 'admin'];

export default function AdminUsers() {
  const { data, error, refresh } = useCoreData('/api/admin/users');
  const [role, setRole] = useState('');
  const [search, setSearch] = useState('');
  const term = search.trim().toLowerCase();
  const people = (data?.users || []).filter(person =>
    (!role || person.role === role) &&
    (!term || person.name.toLowerCase().includes(term) || person.email.toLowerCase().includes(term)));

  return <>
    <PageHeader title="User Directory" subtitle="Every registered account and the role it holds."
      breadcrumbs={[{ label: 'Administration', to: '/admin' }, { label: 'User Directory' }]}
      actions={<Button variant="secondary" icon={RefreshCw} onClick={refresh}>Refresh</Button>} />
    {error && <p role="alert" className="mi-error">{error}</p>}
    {!data && !error && <p role="status">Loading the user directory…</p>}

    {data && <>
      <div className="mi-admin-grid">
        {ROLES.map(value => <MetricTile key={value} label={`${ROLE_LABEL[value]}s`} value={data.counts[value] ?? 0} />)}
        <MetricTile label="Total accounts" value={data.total} />
      </div>

      <Card>
        <CardHeader title="Registered accounts"
          description="Roles come from the email domain at registration. The administrator role is granted locally and cannot be obtained by registering."
          tooltip="Assignments counts the modules an account is attached to in any trimester. It says nothing about whether that person submitted feedback." />
        <div className="px-5 py-4">
          <div className="mi-admin-form mb-4">
            <label htmlFor="role">Role
              <select id="role" value={role} onChange={event => setRole(event.target.value)}
                className="w-full rounded-md border border-slate-300 bg-white p-3">
                <option value="">All roles</option>
                {ROLES.map(value => <option key={value} value={value}>{ROLE_LABEL[value]}</option>)}
              </select>
            </label>
            <label htmlFor="search">Search
              <input id="search" type="search" value={search} onChange={event => setSearch(event.target.value)}
                placeholder="Name or email" className="w-full rounded-md border border-slate-300 bg-white p-3" />
            </label>
          </div>

          {people.length === 0
            ? <EmptyState title="No matching accounts" message="Adjust the role filter or clear the search." />
            : <div className="overflow-x-auto">
              <table className="mi-analytics-table">
                <caption className="sr-only">Registered accounts with their roles and module assignment counts</caption>
                <thead><tr>
                  <th scope="col">Name</th><th scope="col">Email</th><th scope="col">Role</th>
                  <th scope="col">Assignments</th><th scope="col">Registered</th>
                </tr></thead>
                <tbody>{people.map(person => <tr key={person.user_id}>
                  <th scope="row">{person.name}</th>
                  <td className="break-all">{person.email}</td>
                  <td><RoleBadge role={person.role} /></td>
                  <td>{person.assignments}</td>
                  <td>{person.created_at ? dateLabel(person.created_at) : '—'}</td>
                </tr>)}</tbody>
              </table>
            </div>}
          <p className="mi-muted mt-4">Showing {people.length} of {data.total} accounts.</p>
        </div>
      </Card>
    </>}
  </>;
}

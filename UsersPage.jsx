import { useCallback, useEffect, useState } from 'react';
import { api } from '../services/api';
import { Alert } from '../components/Alert.jsx';
import { Pagination } from '../components/Pagination.jsx';
import { formatDate } from '../utils/format.js';

export function UsersPage() {
  const [users, setUsers] = useState([]);
  const [meta, setMeta] = useState({ page: 1, page_size: 10, total_pages: 1, total: 0 });
  const [filters, setFilters] = useState({ search: '', role: '', is_active: '' });
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  const load = useCallback(async (page = meta.page) => {
    try {
      const params = { ...filters, page, page_size: meta.page_size };
      if (params.is_active === '') delete params.is_active;
      const response = await api.users.list(params);
      setUsers(response.items || []);
      setMeta(response);
    } catch (err) {
      setError(err.message);
    }
  }, [filters, meta.page, meta.page_size]);

  useEffect(() => { load(1); }, [load]);

  async function changeRole(user, role) {
    try {
      await api.users.update(user.id, { role });
      setMessage('User role updated.');
      await load(meta.page);
    } catch (err) {
      setError(err.message);
    }
  }

  async function toggleActive(user) {
    try {
      await api.users.update(user.id, { is_active: !user.is_active });
      setMessage('User status updated.');
      await load(meta.page);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <section className="page">
      <div className="page-header"><div><h1>Users</h1><p>Admin-only user directory and role control.</p></div></div>
      <Alert type="danger" onClose={() => setError('')}>{error}</Alert>
      <Alert type="success" onClose={() => setMessage('')}>{message}</Alert>

      <div className="toolbar compact">
        <input placeholder="Search name or email" value={filters.search} onChange={(e) => setFilters({ ...filters, search: e.target.value })} />
        <select value={filters.role} onChange={(e) => setFilters({ ...filters, role: e.target.value })}>
          <option value="">All roles</option>
          <option value="admin">Admin</option>
          <option value="member">Member</option>
        </select>
        <select value={filters.is_active} onChange={(e) => setFilters({ ...filters, is_active: e.target.value })}>
          <option value="">All statuses</option>
          <option value="true">Active</option>
          <option value="false">Inactive</option>
        </select>
        <button className="secondary" onClick={() => load(1)}>Apply</button>
      </div>

      <div className="panel table-panel">
        <table>
          <thead><tr><th>ID</th><th>Name</th><th>Email</th><th>Role</th><th>Status</th><th>Created</th><th>Actions</th></tr></thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.id}>
                <td>#{user.id}</td>
                <td>{user.full_name}</td>
                <td>{user.email}</td>
                <td><span className="badge">{user.role}</span></td>
                <td><span className={user.is_active ? 'badge ok' : 'badge muted'}>{user.is_active ? 'active' : 'inactive'}</span></td>
                <td>{formatDate(user.created_at)}</td>
                <td className="row-actions">
                  <select value={user.role} onChange={(e) => changeRole(user, e.target.value)}>
                    <option value="admin">admin</option>
                    <option value="member">member</option>
                  </select>
                  <button className="secondary small" onClick={() => toggleActive(user)}>{user.is_active ? 'Deactivate' : 'Activate'}</button>
                </td>
              </tr>
            ))}
            {!users.length && <tr><td colSpan="7" className="empty-cell">No users found.</td></tr>}
          </tbody>
        </table>
      </div>
      <Pagination page={meta.page} totalPages={meta.total_pages} total={meta.total} onChange={load} />
    </section>
  );
}

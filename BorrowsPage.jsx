import { useCallback, useEffect, useState } from 'react';
import { Check, RotateCw, X } from 'lucide-react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext.jsx';
import { Alert } from '../components/Alert.jsx';
import { Pagination } from '../components/Pagination.jsx';
import { formatDate } from '../utils/format.js';

export function BorrowsPage() {
  const { user, isAdmin } = useAuth();
  const [records, setRecords] = useState([]);
  const [meta, setMeta] = useState({ page: 1, page_size: 10, total_pages: 1, total: 0 });
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  const load = useCallback(async (page = meta.page) => {
    setLoading(true);
    setError('');

    try {
      const params = { page, page_size: meta.page_size, status };
      const response = isAdmin ? await api.borrows.list(params) : await api.borrows.history(user.id, params);
      setRecords(response.items || []);
      setMeta(response);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [isAdmin, meta.page, meta.page_size, status, user.id]);

  useEffect(() => {
    load(1);
  }, [load]);

  async function returnRecord(record) {
    setError('');

    try {
      await api.borrows.returnBook(record.id, { notes: 'Returned from frontend dashboard' });
      setMessage('Book returned successfully.');
      await load(meta.page);
    } catch (err) {
      setError(err.message);
    }
  }

  async function approveRecord(record) {
    setError('');

    try {
      await api.borrows.approve(record.id);
      setMessage('Borrow request approved.');
      await load(meta.page);
    } catch (err) {
      setError(err.message);
    }
  }

  async function rejectRecord(record) {
    setError('');

    try {
      await api.borrows.reject(record.id, { notes: 'Rejected from frontend dashboard' });
      setMessage('Borrow request rejected.');
      await load(meta.page);
    } catch (err) {
      setError(err.message);
    }
  }

  async function markOverdue() {
    setError('');

    try {
      const result = await api.borrows.markOverdue();
      setMessage(result.message || 'Overdue scan complete.');
      await load(meta.page);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <h1>Borrowing</h1>
          <p>Track borrowed books, due dates, returns, and history.</p>
        </div>
        {isAdmin && (
          <button className="secondary" type="button" onClick={markOverdue}>
            Mark overdue
          </button>
        )}
      </div>

      <Alert type="danger" onClose={() => setError('')}>
        {error}
      </Alert>
      <Alert type="success" onClose={() => setMessage('')}>
        {message}
      </Alert>

      <div className="toolbar compact">
        <select value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All statuses</option>
          <option value="pending">Pending</option>
          <option value="active">Active</option>
          <option value="returned">Returned</option>
          <option value="overdue">Overdue</option>
          <option value="rejected">Rejected</option>
        </select>
        <button className="secondary" type="button" onClick={() => load(1)}>
          <RotateCw size={16} /> Apply
        </button>
      </div>

      <div className="panel table-panel">
        {loading ? (
          <div className="loader-line">Loading borrow records...</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Book</th>
                {isAdmin && <th>User</th>}
                <th>Status</th>
                <th>Requested</th>
                <th>Duration</th>
                <th>Due</th>
                <th>Returned</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {records.map((record) => (
                <tr key={record.id}>
                  <td>#{record.id}</td>
                  <td>{record.book?.title || `Book #${record.book_id}`}</td>
                  {isAdmin && <td>{record.user?.email || `User #${record.user_id}`}</td>}
                  <td>
                    <span className={`badge status-${record.status}`}>{record.status}</span>
                  </td>
                  <td>{formatDate(record.borrowed_at)}</td>
                  <td>{record.requested_duration_days ? `${record.requested_duration_days} days` : '--'}</td>
                  <td>{formatDate(record.due_date)}</td>
                  <td>{record.returned_at ? formatDate(record.returned_at) : '--'}</td>
                  <td>
                    {isAdmin && record.status === 'pending' ? (
                      <div className="row-actions">
                        <button className="primary small" type="button" onClick={() => approveRecord(record)}>
                          <Check size={14} /> Approve
                        </button>
                        <button className="danger small" type="button" onClick={() => rejectRecord(record)}>
                          <X size={14} /> Reject
                        </button>
                      </div>
                    ) : ['active', 'overdue'].includes(record.status) ? (
                      <button className="secondary small" type="button" onClick={() => returnRecord(record)}>
                        Return
                      </button>
                    ) : (
                      '--'
                    )}
                  </td>
                </tr>
              ))}
              {!records.length && (
                <tr>
                  <td colSpan={isAdmin ? 9 : 8} className="empty-cell">
                    No borrow records found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>

      <Pagination page={meta.page} totalPages={meta.total_pages} total={meta.total} onChange={load} />
    </section>
  );
}

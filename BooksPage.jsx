import { useCallback, useEffect, useState } from 'react';
import { Clock, Plus, Search, RotateCw } from 'lucide-react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext.jsx';
import { Alert } from '../components/Alert.jsx';
import { Modal } from '../components/Modal.jsx';
import { Pagination } from '../components/Pagination.jsx';
import { BookForm } from '../components/BookForm.jsx';

export function BooksPage() {
  const { user, isAdmin } = useAuth();

  const [books, setBooks] = useState([]);
  const [meta, setMeta] = useState({ page: 1, page_size: 8, total_pages: 1, total: 0 });
  const [filters, setFilters] = useState({ search: '', genre: '', author: '', available_only: false });
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [modal, setModal] = useState(null);
  const [borrowDuration, setBorrowDuration] = useState(14);

  const load = useCallback(async (page = meta.page) => {
    setLoading(true);
    setError('');

    try {
      const response = await api.books.list({ ...filters, page, page_size: meta.page_size });
      setBooks(response.items || []);
      setMeta(response);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [filters, meta.page, meta.page_size]);

  useEffect(() => {
    load(1);
  }, [load]);

  async function saveBook(data) {
    setError('');
    setSaving(true);

    try {
      if (modal?.book) await api.books.update(modal.book.id, data);
      else await api.books.create(data);

      setModal(null);
      setMessage('Book saved successfully.');
      await load(1);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function deleteBook(book) {
    if (!confirm(`Delete "${book.title}"?`)) return;

    setError('');

    try {
      await api.books.remove(book.id);
      setMessage('Book deleted successfully.');
      await load(meta.page);
    } catch (err) {
      setError(err.message);
    }
  }

  function borrowBook(book) {
    if (!book.is_available) {
      setError('This book is currently unavailable.');
      return;
    }

    setError('');
    setBorrowDuration(14);
    setModal({ type: 'borrow', book });
  }

  async function submitBorrow(event) {
    event.preventDefault();

    const durationDays = Number(borrowDuration);
    if (!Number.isInteger(durationDays) || durationDays < 1) {
      setError('Please enter a valid borrowing duration.');
      return;
    }

    setError('');
    setSaving(true);

    try {
      await api.borrows.create({
        book_id: modal.book.id,
        duration_days: durationDays,
        notes: 'Borrow request from frontend dashboard',
      });
      setModal(null);
      setMessage(`Borrow request sent: ${modal.book.title}`);
      await load(meta.page);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  function updateFilter(field, value) {
    setFilters((current) => ({ ...current, [field]: value }));
  }

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <h1>Books</h1>
          <p>Browse, filter, borrow, and manage library books.</p>
        </div>
        {isAdmin && (
          <button className="primary" type="button" onClick={() => setModal({ type: 'create' })}>
            <Plus size={18} /> Add book
          </button>
        )}
      </div>

      <Alert type="danger" onClose={() => setError('')}>
        {error}
      </Alert>
      <Alert type="success" onClose={() => setMessage('')}>
        {message}
      </Alert>

      <div className="toolbar">
        <div className="search-box">
          <Search size={17} />
          <input
            placeholder="Search title or author"
            value={filters.search}
            onChange={(e) => updateFilter('search', e.target.value)}
          />
        </div>
        <input placeholder="Genre" value={filters.genre} onChange={(e) => updateFilter('genre', e.target.value)} />
        <input placeholder="Author" value={filters.author} onChange={(e) => updateFilter('author', e.target.value)} />
        <label className="inline-check">
          <input
            type="checkbox"
            checked={filters.available_only}
            onChange={(e) => updateFilter('available_only', e.target.checked)}
          />
          Available only
        </label>
        <button className="secondary" type="button" onClick={() => load(1)}>
          <RotateCw size={16} /> Apply
        </button>
      </div>

      {loading ? (
        <div className="loader-line">Loading books...</div>
      ) : (
        <div className="books-grid">
          {books.map((book) => (
            <article className="book-card" key={book.id}>
              <div className="book-top">
                <span className={book.is_available ? 'badge ok' : 'badge muted'}>
                  {book.available_copies}/{book.total_copies} available
                </span>
                <span className="badge">{book.genre || 'Uncategorized'}</span>
              </div>
              <h3>{book.title}</h3>
              <p className="author">by {book.author}</p>
              <p className="description">{book.description || 'No description available.'}</p>
              <dl>
                <div>
                  <dt>ISBN</dt>
                  <dd>{book.isbn || '--'}</dd>
                </div>
                <div>
                  <dt>Year</dt>
                  <dd>{book.published_year || '--'}</dd>
                </div>
              </dl>
              <div className="card-actions">
                {!isAdmin && (
                  <button className="primary" type="button" disabled={!book.is_available} onClick={() => borrowBook(book)}>
                    {book.is_available ? <><Clock size={16} /> Request</> : 'Unavailable'}
                  </button>
                )}
                {isAdmin && (
                  <button className="secondary" type="button" onClick={() => setModal({ type: 'edit', book })}>
                    Edit
                  </button>
                )}
                {isAdmin && (
                  <button className="danger" type="button" onClick={() => deleteBook(book)}>
                    Delete
                  </button>
                )}
              </div>
            </article>
          ))}
        </div>
      )}

      <Pagination page={meta.page} totalPages={meta.total_pages} total={meta.total} onChange={load} />

      {modal && (
        <Modal
          title={modal.type === 'borrow' ? 'Request borrow' : modal.book ? 'Edit book' : 'Add book'}
          onClose={() => setModal(null)}
        >
          {modal.type === 'borrow' ? (
            <form className="form-grid" onSubmit={submitBorrow}>
              <label className="wide">
                Requesting as
                <input value={`${user?.full_name || 'Member'} (${user?.email || ''})`} disabled />
              </label>
              <label className="wide">
                Book
                <input value={modal.book.title} disabled />
              </label>

              <label>
                Duration (days)
                <input
                  type="number"
                  min="1"
                  max="14"
                  value={borrowDuration}
                  onChange={(event) => setBorrowDuration(event.target.value)}
                  required
                />
                <span className="field-hint">Maximum 14 days</span>
              </label>
              <div className="card-actions wide">
                <button className="primary" type="submit" disabled={saving}>
                  <Clock size={16} /> {saving ? 'Sending...' : 'Send request'}
                </button>
                <button className="secondary" type="button" onClick={() => setModal(null)}>
                  Cancel
                </button>
              </div>
            </form>
          ) : (
            <BookForm initialValue={modal.book} onSubmit={saveBook} loading={saving} />
          )}
        </Modal>
      )}
    </section>
  );
}

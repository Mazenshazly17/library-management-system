import { useEffect, useState } from 'react';

const emptyBook = {
  title: '',
  author: '',
  isbn: '',
  genre: '',
  published_year: '',
  total_copies: 1,
  description: '',
};

export function BookForm({ initialValue, onSubmit, loading }) {
  const [form, setForm] = useState(emptyBook);

  useEffect(() => {
    if (initialValue) {
      setForm({
        title: initialValue.title || '',
        author: initialValue.author || '',
        isbn: initialValue.isbn || '',
        genre: initialValue.genre || '',
        published_year: initialValue.published_year || '',
        total_copies: initialValue.total_copies || 1,
        description: initialValue.description || '',
      });
    } else {
      setForm(emptyBook);
    }
  }, [initialValue]);

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function submit(event) {
    event.preventDefault();
    onSubmit({
      ...form,
      total_copies: Number(form.total_copies),
      published_year: form.published_year ? Number(form.published_year) : undefined,
    });
  }

  return (
    <form className="form-grid" onSubmit={submit}>
      <label>Title<input required value={form.title} onChange={(e) => update('title', e.target.value)} /></label>
      <label>Author<input required value={form.author} onChange={(e) => update('author', e.target.value)} /></label>
      <label>ISBN<input value={form.isbn} onChange={(e) => update('isbn', e.target.value)} placeholder="10 or 13 digits" /></label>
      <label>Genre<input value={form.genre} onChange={(e) => update('genre', e.target.value)} /></label>
      <label>Published Year<input type="number" min="1000" max="2100" value={form.published_year} onChange={(e) => update('published_year', e.target.value)} /></label>
      <label>Total Copies<input type="number" min="1" max="1000" required value={form.total_copies} onChange={(e) => update('total_copies', e.target.value)} /></label>
      <label className="wide">Description<textarea rows="4" value={form.description} onChange={(e) => update('description', e.target.value)} /></label>
      <button className="primary wide" disabled={loading}>{loading ? 'Saving...' : 'Save book'}</button>
    </form>
  );
}

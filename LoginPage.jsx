import { useState } from 'react';
import { BookOpenCheck, LockKeyhole, UserPlus } from 'lucide-react';
import { useAuth } from '../context/AuthContext.jsx';
import { Alert } from '../components/Alert.jsx';

export function LoginPage() {
  const { login, register } = useAuth();
  const [mode, setMode] = useState('login');
  const [form, setForm] = useState({ full_name: '', email: '', password: '' });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function submit(event) {
    event.preventDefault();
    setError('');
    setSuccess('');

    if (mode === 'register' && !/\d/.test(form.password)) {
      setError('Password must contain at least one digit.');
      return;
    }

    setLoading(true);
    try {
      if (mode === 'login') {
        await login({ email: form.email, password: form.password });
      } else {
        await register({ full_name: form.full_name, email: form.email, password: form.password });
        setSuccess('Account created. You can login now.');
        setMode('login');
      }
    } catch (err) {
      setError(err.message || 'Operation failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-layout">
      <section className="auth-hero">
        <div className="hero-badge"><BookOpenCheck size={22} /> Library Management System</div>
        <h1>Professional frontend for your FastAPI backend.</h1>
        <p>JWT authentication, role-based UI, books CRUD, borrowing workflow, pagination, filtering, health monitoring, and admin user management.</p>
        <div className="hero-grid">
          <span>FastAPI API</span><span>JWT Secure</span><span>Redis Ready</span><span>Admin/Member</span>
        </div>
      </section>
      <section className="auth-card">
        <div className="auth-title">
          {mode === 'login' ? <LockKeyhole size={24} /> : <UserPlus size={24} />}
          <div>
            <h2>{mode === 'login' ? 'Login' : 'Create account'}</h2>
            <p>{mode === 'login' ? 'Access the library dashboard.' : 'Register a member account.'}</p>
          </div>
        </div>

        <Alert type="danger">{error}</Alert>
        <Alert type="success">{success}</Alert>

        <form onSubmit={submit} className="auth-form">
          {mode === 'register' && (
            <label>Full name<input required minLength="2" value={form.full_name} onChange={(e) => update('full_name', e.target.value)} /></label>
          )}
          <label>Email<input required type="email" value={form.email} onChange={(e) => update('email', e.target.value)} /></label>
          <label>
            Password
            <input required type="password" minLength="8" value={form.password} onChange={(e) => update('password', e.target.value)} />
            {mode === 'register' && <small className="field-hint">At least 8 characters and one digit.</small>}
          </label>
          <button className="primary" disabled={loading}>{loading ? 'Please wait...' : mode === 'login' ? 'Login' : 'Register'}</button>
        </form>

        <button className="link-btn" onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError(''); setSuccess(''); }}>
          {mode === 'login' ? 'Need an account? Register' : 'Already have an account? Login'}
        </button>
      </section>
    </main>
  );
}

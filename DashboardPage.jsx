import { useEffect, useState } from 'react';
import { BookOpen, Clock, Database, Users } from 'lucide-react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext.jsx';
import { Alert } from '../components/Alert.jsx';

export function DashboardPage({ onNavigate }) {
  const { isAdmin } = useAuth();
  const [stats, setStats] = useState({ books: null, borrows: null, users: null, health: null });
  const [error, setError] = useState('');

  useEffect(() => {
    async function load() {
      try {
        const [books, borrows, health] = await Promise.all([
          api.books.list({ page: 1, page_size: 1 }),
          api.borrows.list({ page: 1, page_size: 1 }),
          api.health(),
        ]);

        let users = null;
        if (isAdmin) users = await api.users.list({ page: 1, page_size: 1 });

        setStats({ books, borrows, users, health });
      } catch (err) {
        setError(err.message);
      }
    }

    load();
  }, [isAdmin]);

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <h1>Dashboard</h1>
          <p>System overview and quick actions.</p>
        </div>
      </div>

      <Alert type="danger">{error}</Alert>

      <div className="stats-grid">
        <Stat icon={BookOpen} label="Books" value={stats.books?.total ?? '--'} onClick={() => onNavigate('books')} />
        <Stat icon={Clock} label="Borrow records" value={stats.borrows?.total ?? '--'} onClick={() => onNavigate('borrows')} />
        <Stat icon={Database} label="System" value={stats.health?.status || '--'} onClick={() => onNavigate('health')} />
        {isAdmin && <Stat icon={Users} label="Users" value={stats.users?.total ?? '--'} onClick={() => onNavigate('users')} />}
      </div>

      <div className="panel">
        <h2>Implemented project requirements</h2>
        <div className="check-grid">
          {[
            'JWT Auth',
            'Role-Based UI',
            'Books CRUD',
            'Borrow/Return',
            'Pagination',
            'Filtering',
            'Health Check',
            'Admin Users',
          ].map((item) => (
            <span key={item}>OK {item}</span>
          ))}
        </div>
      </div>
    </section>
  );
}

function Stat({ icon: Icon, label, value, onClick }) {
  return (
    <button className="stat-card" type="button" onClick={onClick}>
      <Icon size={22} />
      <span>{label}</span>
      <strong>{value}</strong>
    </button>
  );
}

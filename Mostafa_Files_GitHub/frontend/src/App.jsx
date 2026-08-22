import { useEffect, useState } from 'react';
import { BookOpen, LayoutDashboard, LogOut, ShieldCheck, UserRound, Users, Activity } from 'lucide-react';
import { useAuth } from './context/AuthContext.jsx';
import { LoginPage } from './pages/LoginPage.jsx';
import { DashboardPage } from './pages/DashboardPage.jsx';
import { BooksPage } from './pages/BooksPage.jsx';
import { BorrowsPage } from './pages/BorrowsPage.jsx';
import { UsersPage } from './pages/UsersPage.jsx';
import { HealthPage } from './pages/HealthPage.jsx';

const tabs = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'books', label: 'Books', icon: BookOpen },
  { id: 'borrows', label: 'Borrowing', icon: ShieldCheck },
  { id: 'health', label: 'Health', icon: Activity },
];

export default function App() {
  const { user, booting, isAuthenticated, isAdmin, logout } = useAuth();
  const [activeTab, setActiveTab] = useState('dashboard');

  useEffect(() => {
    if (!isAdmin && activeTab === 'users') setActiveTab('dashboard');
  }, [isAdmin, activeTab]);

  if (booting) {
    return <div className="boot-screen"><div className="spinner" /> Restoring secure session...</div>;
  }

  if (!isAuthenticated) return <LoginPage />;

  const visibleTabs = isAdmin ? [...tabs, { id: 'users', label: 'Users', icon: Users }] : tabs;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">L</div>
          <div>
            <strong>Library MS</strong>
            <span>FastAPI Control Panel</span>
          </div>
        </div>

        <nav className="nav-list">
          {visibleTabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button key={tab.id} className={activeTab === tab.id ? 'nav-item active' : 'nav-item'} onClick={() => setActiveTab(tab.id)}>
                <Icon size={18} />
                {tab.label}
              </button>
            );
          })}
        </nav>

        <div className="profile-card">
          <div className="avatar"><UserRound size={18} /></div>
          <div className="profile-meta">
            <strong>{user?.full_name || 'User'}</strong>
            <span>{user?.email}</span>
            <em>{user?.role}</em>
          </div>
        </div>

        <button className="logout-btn" onClick={logout}>
          <LogOut size={18} /> Logout
        </button>
      </aside>

      <main className="main-content">
        {activeTab === 'dashboard' && <DashboardPage onNavigate={setActiveTab} />}
        {activeTab === 'books' && <BooksPage />}
        {activeTab === 'borrows' && <BorrowsPage />}
        {activeTab === 'health' && <HealthPage />}
        {activeTab === 'users' && isAdmin && <UsersPage />}
      </main>
    </div>
  );
}

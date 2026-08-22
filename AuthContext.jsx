import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { api } from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const raw = localStorage.getItem('library_user');
    try {
      return raw ? JSON.parse(raw) : null;
    } catch {
      localStorage.removeItem('library_user');
      return null;
    }
  });
  const [token, setToken] = useState(() => localStorage.getItem('library_access_token'));
  const [booting, setBooting] = useState(Boolean(localStorage.getItem('library_access_token')));

  const logoutLocal = useCallback(() => {
    localStorage.removeItem('library_access_token');
    localStorage.removeItem('library_user');
    setToken(null);
    setUser(null);
  }, []);

  useEffect(() => {
    let mounted = true;
    async function restoreSession() {
      if (!token) {
        setBooting(false);
        return;
      }
      try {
        const me = await api.auth.me();
        if (!mounted) return;
        setUser(me);
        localStorage.setItem('library_user', JSON.stringify(me));
      } catch {
        logoutLocal();
      } finally {
        if (mounted) setBooting(false);
      }
    }
    restoreSession();
    return () => { mounted = false; };
  }, [token, logoutLocal]);

  const saveSession = useCallback((payload) => {
    localStorage.setItem('library_access_token', payload.access_token);
    localStorage.setItem('library_user', JSON.stringify(payload.user));
    setToken(payload.access_token);
    setUser(payload.user);
  }, []);

  const login = useCallback(async (credentials) => {
    logoutLocal();
    const payload = await api.auth.login(credentials);
    saveSession(payload);
    return payload;
  }, [logoutLocal, saveSession]);


  const register = useCallback(async (data) => {
    return api.auth.register(data);
  }, []);

  const logout = useCallback(async () => {
    try {
      if (token) await api.auth.logout();
    } finally {
      logoutLocal();
    }
  }, [logoutLocal, token]);

  const value = useMemo(() => ({
    user,
    token,
    booting,
    isAuthenticated: Boolean(token && user),
    isAdmin: user?.role === 'admin' || user?.role === 'librarian',
    login,
    register,
    logout,
  }), [user, token, booting, login, register, logout]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}
